import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from models import (
    db, Election, Position, Candidate, EligibilityRule,
    Student, UniversityRecord, VoterParticipation, Vote,
    Notification, AuditLog, Admin
)
from services.audit_service import AuditService
from services.notification_service import NotificationService
from services.election_service import ElectionService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
def admin_only():
    """Ensure that only authenticated administrators access this blueprint."""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.admin_login', next=request.path))
    if not current_user.is_admin:
        flash('Access restricted to Electoral Commission officials and administrators.', 'danger')
        return redirect(url_for('main.index'))


@admin_bp.route('/dashboard')
def dashboard():
    """Admin Control Cockpit with live KPI metrics, active elections, and recent audit trail."""
    ElectionService.auto_update_election_statuses()

    total_students = Student.query.count()
    total_uni_records = UniversityRecord.query.count()
    total_elections = Election.query.count()
    active_elections = Election.query.filter_by(status='active').count()
    total_candidates = Candidate.query.count()
    total_participations = VoterParticipation.query.count()

    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    elections = Election.query.order_by(Election.created_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_uni_records=total_uni_records,
        total_elections=total_elections,
        active_elections=active_elections,
        total_candidates=total_candidates,
        total_participations=total_participations,
        recent_logs=recent_logs,
        elections=elections
    )


@admin_bp.route('/elections', methods=['GET', 'POST'])
def elections():
    """Manage election creation, scheduling, and lifecycle states."""
    ElectionService.auto_update_election_statuses()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        academic_year = request.form.get('academic_year', '').strip()
        start_str = request.form.get('start_time', '').strip()
        end_str = request.form.get('end_time', '').strip()
        status = request.form.get('status', 'draft')

        if not title or not academic_year or not start_str or not end_str:
            flash('Title, academic year, and scheduled dates are required.', 'warning')
            return redirect(url_for('admin.elections'))

        try:
            start_time = datetime.strptime(start_str, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_str, '%Y-%m-%dT%H:%M')

            if end_time <= start_time:
                flash('End time must be after the start time.', 'danger')
                return redirect(url_for('admin.elections'))

            election = Election(
                title=title,
                description=description,
                academic_year=academic_year,
                start_time=start_time,
                end_time=end_time,
                status=status,
                created_by=current_user.id
            )
            db.session.add(election)
            db.session.commit()

            AuditService.log_action(
                user_type='admin',
                user_identifier=current_user.username,
                action='CREATE_ELECTION',
                details=f"Created election '{title}' (ID {election.id}), Schedule: {start_time} to {end_time}",
                ip_address=request.remote_addr
            )

            flash(f"Election '{title}' created successfully.", 'success')
            return redirect(url_for('admin.election_detail', election_id=election.id))

        except ValueError as ve:
            flash(f"Invalid date/time format: {ve}", 'danger')

    all_elections = Election.query.order_by(Election.created_at.desc()).all()
    return render_template('admin/elections.html', elections=all_elections)


@admin_bp.route('/elections/<int:election_id>', methods=['GET', 'POST'])
def election_detail(election_id):
    """Detailed election control room: edit schedule, add positions, set eligibility rules."""
    election = Election.query.get_or_404(election_id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_status':
            new_status = request.form.get('status')
            if new_status in ('draft', 'scheduled', 'active', 'paused', 'closed'):
                old_status = election.status
                election.status = new_status
                db.session.commit()

                AuditService.log_action(
                    user_type='admin',
                    user_identifier=current_user.username,
                    action='ELECTION_STATUS_CHANGE',
                    details=f"Election ID {election.id} status changed from {old_status} to {new_status}",
                    ip_address=request.remote_addr
                )
                NotificationService.send_election_broadcast(election, new_status)
                flash(f"Election status changed to {new_status.upper()}.", 'success')

        elif action == 'add_position':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            max_sel = int(request.form.get('max_selections', 1))
            priority = int(request.form.get('priority_order', 1))

            if title:
                pos = Position(
                    election_id=election.id,
                    title=title,
                    description=description,
                    max_selections=max_sel,
                    priority_order=priority
                )
                db.session.add(pos)
                db.session.commit()

                AuditService.log_action(
                    user_type='admin',
                    user_identifier=current_user.username,
                    action='ADD_POSITION',
                    details=f"Added position '{title}' to Election ID {election.id}",
                    ip_address=request.remote_addr
                )
                flash(f"Position '{title}' added successfully.", 'success')

        elif action == 'add_rule':
            pos_id = int(request.form.get('position_id'))
            campus = request.form.get('campus', 'ALL')
            faculty = request.form.get('faculty', 'ALL')
            course = request.form.get('course', 'ALL')
            year_of_study = int(request.form.get('year_of_study', 0))
            gender = request.form.get('gender', 'ALL')

            rule = EligibilityRule(
                election_id=election.id,
                position_id=pos_id,
                campus=campus,
                faculty=faculty,
                course=course,
                year_of_study=year_of_study,
                gender=gender
            )
            db.session.add(rule)
            db.session.commit()

            AuditService.log_action(
                user_type='admin',
                user_identifier=current_user.username,
                action='ADD_ELIGIBILITY_RULE',
                details=f"Added rule to Pos {pos_id}: Campus={campus}, Faculty={faculty}, Year={year_of_study}",
                ip_address=request.remote_addr
            )
            flash('Eligibility rule added successfully.', 'success')

        return redirect(url_for('admin.election_detail', election_id=election.id))

    positions = Position.query.filter_by(election_id=election.id).order_by(Position.priority_order).all()
    campuses = current_app.config.get('CAMPUSES', [])
    faculties = current_app.config.get('FACULTIES', [])

    return render_template(
        'admin/election_detail.html',
        election=election,
        positions=positions,
        campuses=campuses,
        faculties=faculties
    )


@admin_bp.route('/elections/<int:election_id>/position/<int:position_id>/delete', methods=['POST'])
def delete_position(election_id, position_id):
    """Delete a position from an election."""
    pos = Position.query.filter_by(id=position_id, election_id=election_id).first_or_404()
    title = pos.title
    db.session.delete(pos)
    db.session.commit()

    AuditService.log_action(
        user_type='admin',
        user_identifier=current_user.username,
        action='DELETE_POSITION',
        details=f"Deleted position '{title}' from Election ID {election_id}",
        ip_address=request.remote_addr
    )
    flash(f"Position '{title}' deleted.", 'info')
    return redirect(url_for('admin.election_detail', election_id=election_id))


@admin_bp.route('/candidates', methods=['GET', 'POST'])
def candidates():
    """Candidate management: screening, registration, and status updates."""
    if request.method == 'POST':
        election_id = int(request.form.get('election_id'))
        position_id = int(request.form.get('position_id'))
        full_name = request.form.get('full_name', '').strip()
        course = request.form.get('course', '').strip()
        campus = request.form.get('campus', '').strip()
        symbol_name = request.form.get('symbol_name', '').strip()
        manifesto = request.form.get('manifesto', '').strip()
        status = request.form.get('status', 'approved')

        # Handle image uploads
        photo_file = request.files.get('photo')
        photo_url = None
        if photo_file and photo_file.filename:
            filename = secure_filename(f"cand_{election_id}_{position_id}_{photo_file.filename}")
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            photo_file.save(upload_path)
            photo_url = f"/static/uploads/{filename}"

        symbol_file = request.files.get('symbol')
        symbol_url = None
        if symbol_file and symbol_file.filename:
            sym_filename = secure_filename(f"sym_{election_id}_{position_id}_{symbol_file.filename}")
            sym_path = os.path.join(current_app.config['UPLOAD_FOLDER'], sym_filename)
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            symbol_file.save(sym_path)
            symbol_url = f"/static/uploads/{sym_filename}"

        new_cand = Candidate(
            election_id=election_id,
            position_id=position_id,
            full_name=full_name,
            course=course,
            campus=campus,
            symbol_name=symbol_name,
            photo_url=photo_url,
            symbol_url=symbol_url,
            manifesto=manifesto,
            status=status
        )
        db.session.add(new_cand)
        db.session.commit()

        AuditService.log_action(
            user_type='admin',
            user_identifier=current_user.username,
            action='REGISTER_CANDIDATE',
            details=f"Registered candidate '{full_name}' for Position ID {position_id}",
            ip_address=request.remote_addr
        )

        flash(f"Candidate '{full_name}' registered successfully.", 'success')
        return redirect(url_for('admin.candidates', election_id=election_id))

    # GET Candidates
    selected_election_id = request.args.get('election_id', type=int)
    elections_list = Election.query.order_by(Election.created_at.desc()).all()

    query = Candidate.query
    if selected_election_id:
        query = query.filter_by(election_id=selected_election_id)
    all_candidates = query.order_by(Candidate.created_at.desc()).all()

    positions_list = Position.query.all()
    campuses = current_app.config.get('CAMPUSES', [])

    return render_template(
        'admin/candidates.html',
        candidates=all_candidates,
        elections=elections_list,
        positions=positions_list,
        selected_election_id=selected_election_id,
        campuses=campuses
    )


@admin_bp.route('/candidates/<int:candidate_id>/status', methods=['POST'])
def update_candidate_status(candidate_id):
    """Approve or disqualify a candidate."""
    candidate = Candidate.query.get_or_404(candidate_id)
    new_status = request.form.get('status')
    reason = request.form.get('disqualification_reason', '').strip()

    if new_status in ('pending', 'approved', 'disqualified', 'withdrawn'):
        candidate.status = new_status
        if new_status == 'disqualified':
            candidate.disqualification_reason = reason
        db.session.commit()

        AuditService.log_action(
            user_type='admin',
            user_identifier=current_user.username,
            action='CANDIDATE_STATUS_UPDATE',
            details=f"Candidate {candidate.full_name} status updated to {new_status}. Reason: {reason or 'N/A'}",
            ip_address=request.remote_addr
        )

        flash(f"Candidate {candidate.full_name} status updated to {new_status.upper()}.", 'success')

    return redirect(url_for('admin.candidates', election_id=candidate.election_id))


@admin_bp.route('/students')
def students():
    """Browse registered student voters and authoritative University Registrar records."""
    search = request.args.get('q', '').strip()
    campus_filter = request.args.get('campus', '')

    query = Student.query
    if search:
        query = query.filter(
            (Student.student_id.ilike(f"%{search}%")) |
            (Student.reg_no.ilike(f"%{search}%")) |
            (Student.full_name.ilike(f"%{search}%")) |
            (Student.email.ilike(f"%{search}%"))
        )
    if campus_filter:
        query = query.filter_by(campus=campus_filter)

    registered_students = query.order_by(Student.created_at.desc()).limit(100).all()
    campuses = current_app.config.get('CAMPUSES', [])

    return render_template(
        'admin/students.html',
        students=registered_students,
        search=search,
        campus_filter=campus_filter,
        campuses=campuses
    )


@admin_bp.route('/audit-logs')
def audit_logs():
    """View full immutable system and administrative audit log."""
    action_filter = request.args.get('action', '')
    user_type_filter = request.args.get('user_type', '')

    query = AuditLog.query
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    if user_type_filter:
        query = query.filter_by(user_type=user_type_filter)

    logs = query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template('admin/audit_logs.html', logs=logs, action_filter=action_filter, user_type_filter=user_type_filter)
