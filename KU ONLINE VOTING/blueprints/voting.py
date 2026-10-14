from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import db, Election, VoterParticipation, Position, Candidate
from services.election_service import ElectionService

voting_bp = Blueprint('voting', __name__, url_prefix='/voting')

@voting_bp.before_request
def student_only():
    """Ensure that only authenticated students access voting endpoints."""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.student_login', next=request.path))
    if current_user.is_admin:
        flash('Administrators cannot participate directly in student ballots.', 'warning')
        return redirect(url_for('admin.dashboard'))


@voting_bp.route('/elections')
def list_elections():
    """Display available elections and student's voting participation status."""
    ElectionService.auto_update_election_statuses()
    elections = Election.query.filter(Election.status.in_(['active', 'scheduled', 'closed', 'results_published'])).order_by(Election.start_time.desc()).all()

    # Track elections where this student has already participated
    voted_election_ids = {
        vp.election_id for vp in VoterParticipation.query.filter_by(student_id=current_user.id).all()
    }

    election_cards = []
    for el in elections:
        has_voted = el.id in voted_election_ids
        receipt = None
        if has_voted:
            vp = VoterParticipation.query.filter_by(student_id=current_user.id, election_id=el.id).first()
            receipt = vp.receipt_token if vp else None

        eligible_positions = ElectionService.get_eligible_positions_for_student(current_user, el.id)

        election_cards.append({
            'election': el,
            'effective_status': el.get_effective_status(),
            'has_voted': has_voted,
            'receipt_token': receipt,
            'eligible_positions_count': len(eligible_positions),
            'can_vote': (el.is_open() and not has_voted and len(eligible_positions) > 0)
        })

    return render_template('voting/elections.html', elections=election_cards, student=current_user)


@voting_bp.route('/elections/<int:election_id>/ballot')
def show_ballot(election_id):
    """
    Renders the electronic voting booth with only eligible positions and candidates.
    Strictly verifies election state and double-voting prevention.
    """
    election = Election.query.get_or_404(election_id)

    # 1. Prevent double voting
    if ElectionService.has_student_voted(current_user.id, election.id):
        vp = VoterParticipation.query.filter_by(student_id=current_user.id, election_id=election.id).first()
        flash('You have already cast your ballot in this election. Double voting is strictly prevented.', 'info')
        return redirect(url_for('voting.vote_confirmation', election_id=election.id, token=vp.receipt_token if vp else ''))

    # 2. Check election schedule
    if not election.is_open():
        flash('Voting for this election is currently not active or the deadline has passed.', 'warning')
        return redirect(url_for('voting.list_elections'))

    # 3. Retrieve student's eligible positions
    eligible_positions = ElectionService.get_eligible_positions_for_student(current_user, election.id)

    if not eligible_positions:
        flash('There are currently no contested positions matching your campus, faculty, or course eligibility rules.', 'info')
        return redirect(url_for('voting.list_elections'))

    return render_template(
        'voting/ballot.html',
        election=election,
        positions=eligible_positions,
        student=current_user
    )


@voting_bp.route('/elections/<int:election_id>/cast', methods=['POST'])
def cast_vote(election_id):
    """
    Processes the submitted ballot with atomic database isolation and ballot secrecy.
    """
    election = Election.query.get_or_404(election_id)

    # 1. Check double voting
    if ElectionService.has_student_voted(current_user.id, election.id):
        flash('Double voting is prohibited. You have already cast your ballot.', 'danger')
        return redirect(url_for('voting.list_elections'))

    # 2. Check active schedule
    if not election.is_open():
        flash('Voting deadline has passed. Ballot rejected.', 'danger')
        return redirect(url_for('voting.list_elections'))

    # 3. Parse submitted votes
    # Expected form input: position_{pos_id} = candidate_id or 'abstain'
    eligible_positions = ElectionService.get_eligible_positions_for_student(current_user, election.id)
    eligible_pos_ids = {pos.id for pos in eligible_positions}

    choices = {}
    for pos in eligible_positions:
        field_name = f"position_{pos.id}"
        val = request.form.get(field_name)

        if not val:
            flash(f"Please make a selection for '{pos.title}' (select a candidate or choose 'Abstain').", 'warning')
            return redirect(url_for('voting.show_ballot', election_id=election.id))

        if val == 'abstain':
            choices[str(pos.id)] = None
        else:
            try:
                choices[str(pos.id)] = int(val)
            except ValueError:
                flash("Invalid vote input detected.", 'danger')
                return redirect(url_for('voting.show_ballot', election_id=election.id))

    # 4. Execute atomic cast with ballot secrecy
    success, receipt_token, msg = ElectionService.cast_ballot(
        student=current_user,
        election=election,
        choices=choices,
        ip_address=request.remote_addr
    )

    if success:
        flash(msg, 'success')
        return redirect(url_for('voting.vote_confirmation', election_id=election.id, token=receipt_token))
    else:
        flash(f"Submission Error: {msg}", 'danger')
        return redirect(url_for('voting.show_ballot', election_id=election.id))


@voting_bp.route('/elections/<int:election_id>/confirmation')
def vote_confirmation(election_id):
    """Displays official participation confirmation screen with cryptographic receipt token."""
    election = Election.query.get_or_404(election_id)
    token = request.args.get('token')

    participation = VoterParticipation.query.filter_by(
        student_id=current_user.id,
        election_id=election.id
    ).first()

    if not participation and not token:
        flash('You have not yet participated in this election.', 'warning')
        return redirect(url_for('voting.list_elections'))

    display_token = token or (participation.receipt_token if participation else "N/A")
    voted_at = participation.voted_at if participation else None

    return render_template(
        'voting/confirmation.html',
        election=election,
        receipt_token=display_token,
        voted_at=voted_at,
        student=current_user
    )
