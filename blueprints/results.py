from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from models import db, Election, utc_now
from services.election_service import ElectionService
from services.audit_service import AuditService
from services.notification_service import NotificationService

results_bp = Blueprint('results', __name__)

@results_bp.route('/results')
def list_published_results():
    """Public list of elections with officially approved and published results."""
    published_elections = Election.query.filter_by(status='results_published').order_by(Election.end_time.desc()).all()
    return render_template('results/index.html', elections=published_elections)


@results_bp.route('/results/<int:election_id>')
def view_public_results(election_id):
    """
    Public and Student view of election results.
    Strictly blocked if results have not yet been approved and published by the Electoral Commission.
    """
    election = Election.query.get_or_404(election_id)

    if election.status != 'results_published':
        # If user is admin, offer them a redirect to the live admin view
        if current_user.is_authenticated and current_user.is_admin:
            flash('These results are not published yet, but you have administrative access to live counts.', 'info')
            return redirect(url_for('results.view_admin_results', election_id=election.id))

        flash('Official results for this election have not yet been published by the Electoral Commission.', 'warning')
        return redirect(url_for('results.list_published_results'))

    data = ElectionService.get_election_results(election_id, allow_unapproved=False)
    if not data:
        abort(404)

    return render_template(
        'results/view.html',
        data=data,
        is_admin_preview=False
    )


@results_bp.route('/admin/results/<int:election_id>')
@login_required
def view_admin_results(election_id):
    """
    Real-time election tabulation and turnout analytics visible ONLY to authorized administrators.
    Allows monitoring during voting and reviewing before official publication.
    """
    if not current_user.is_admin:
        abort(403)

    data = ElectionService.get_election_results(election_id, allow_unapproved=True)
    if not data:
        abort(404)

    election = Election.query.get_or_404(election_id)

    return render_template(
        'results/view.html',
        data=data,
        election=election,
        is_admin_preview=True
    )


@results_bp.route('/admin/results/<int:election_id>/publish', methods=['POST'])
@login_required
def publish_results(election_id):
    """
    Official sign-off gate: Electoral Commission Chair or Super Admin approves and releases results to the public.
    """
    if not current_user.is_admin:
        abort(403)

    if not current_user.can_publish_results:
        flash('Permission denied: Only the Electoral Commission Chair or Super Administrator can publish final results.', 'danger')
        return redirect(url_for('results.view_admin_results', election_id=election_id))

    election = Election.query.get_or_404(election_id)
    election.status = 'results_published'
    election.results_approved_by = current_user.id
    election.results_approved_at = utc_now()
    db.session.commit()

    AuditService.log_action(
        user_type='admin',
        user_identifier=current_user.username,
        action='RESULTS_APPROVED_AND_PUBLISHED',
        details=f"Election ID {election.id} ('{election.title}') results officially certified and released to public.",
        ip_address=request.remote_addr
    )

    NotificationService.create_notification(
        title=f"Official Election Results Published: {election.title}",
        message=f"The Electoral Commission has certified and released the official results for '{election.title}'. View them now on the results portal.",
        target_group='all',
        category='results',
        is_pinned=True,
        created_by=current_user.id
    )

    flash(f"Official election results for '{election.title}' have been certified and published to the public portal.", 'success')
    return redirect(url_for('results.view_public_results', election_id=election.id))


@results_bp.route('/api/results/<int:election_id>')
def api_results(election_id):
    """
    JSON API for dynamic frontend Chart.js rendering.
    Validates permissions before exposing unapproved data.
    """
    election = Election.query.get_or_404(election_id)
    allow_unapproved = False

    if election.status != 'results_published':
        if not (current_user.is_authenticated and current_user.is_admin):
            return jsonify({'error': 'Results not published'}), 403
        allow_unapproved = True

    data = ElectionService.get_election_results(election_id, allow_unapproved=allow_unapproved)
    return jsonify(data)
