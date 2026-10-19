import os
import uuid
from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import current_user
from werkzeug.utils import secure_filename
from models import (
    db, Election, Position, Candidate, EligibilityRule,
    Student, UniversityRecord, VoterParticipation, AuditLog, Admin
)
from services.audit_service import AuditService
from services.notification_service import NotificationService
from services.election_service import ElectionService
from services.admin_service import AdminService, AdminServiceError

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
def admin_only():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.admin_login', next=request.path))
    if not getattr(current_user, 'is_admin', False) or not getattr(current_user, 'is_active', True):
        abort(403)


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return decorator


def _parse_datetime(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise AdminServiceError('Use a valid date and time.') from exc


def _save_image(file_storage, prefix):
    if not file_storage or not file_storage.filename:
        return None
    original = secure_filename(file_storage.filename)
    ext = os.path.splitext(original)[1].lower()
    allowed = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'webp'})
    if ext.lstrip('.') not in allowed:
        raise AdminServiceError('Unsupported image format.')
    filename = f'{prefix}_{uuid.uuid4().hex}{ext}'
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    file_storage.save(os.path.join(upload_dir, filename))
    return f'/static/uploads/{filename}'


@admin_bp.route('/dashboard')
def dashboard():
    ElectionService.auto_update_election_statuses()
    return render_template(
        'admin/dashboard.html',
        total_students=Student.query.count(),
        total_uni_records=UniversityRecord.query.count(),
        total_elections=Election.query.count(),
        active_elections=Election.query.filter_by(status='active').count(),
        total_candidates=Candidate.query.count(),
        total_participations=VoterParticipation.query.count(),
        recent_logs=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all(),
        elections=Election.query.order_by(Election.created_at.desc()).limit(5).all()
    )


@admin_bp.route('/elections', methods=['GET', 'POST'])
@roles_required('super_admin', 'ec_chair')
def elections():
    ElectionService.auto_update_election_statuses()
    if request.method == 'POST':
        try:
            election = AdminService.create_election(
                admin=current_user,
                title=request.form.get('title'),
                description=request.form.get('description'),
                academic_year=request.form.get('academic_year'),
                start_time=_parse_datetime(request.form.get('start_time')),
                end_time=_parse_datetime(request.form.get('end_time')),
                status=request.form.get('status') or 'scheduled',
            )
            AuditService.log_action('admin', current_user.username, 'CREATE_ELECTION',
                                    f"Created election '{election.title}' (ID {election.id}).",
                                    request.remote_addr)
            flash(f"Election '{election.title}' created successfully.", 'success')
            return redirect(url_for('admin.election_detail', election_id=election.id))
        except AdminServiceError as exc:
            flash(str(exc), 'danger')
        except Exception:
            current_app.logger.exception('Unexpected election creation error')
            flash('The election could not be created. Please try again.', 'danger')
    return render_template('admin/elections.html', elections=Election.query.order_by(Election.created_at.desc()).all())


@admin_bp.route('/elections/<int:election_id>', methods=['GET', 'POST'])
def election_detail(election_id):
    election = Election.query.get_or_404(election_id)
    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'update_status':
                if current_user.role not in ('super_admin', 'ec_chair'):
                    abort(403)
                new_status = request.form.get('status')
                if new_status not in ('draft', 'scheduled', 'active', 'paused', 'closed'):
                    raise AdminServiceError('Invalid election status.')
                if new_status == 'active' and not election.positions:
                    raise AdminServiceError('Add at least one position before opening an election.')
                old_status = election.status
                election.status = new_status
                db.session.commit()
                AuditService.log_action('admin', current_user.username, 'ELECTION_STATUS_CHANGE',
                                        f'Election {election.id}: {old_status} -> {new_status}', request.remote_addr)
                if new_status in ('active', 'paused', 'closed'):
                    NotificationService.send_election_broadcast(election, new_status)
                flash(f'Election status changed to {new_status.upper()}.', 'success')

            elif action == 'add_position':
                position = AdminService.add_position(
                    admin=current_user, election_id=election.id,
                    title=request.form.get('title'), description=request.form.get('description'),
                    max_selections=request.form.get('max_selections', 1),
                    priority_order=request.form.get('priority_order', 1),
                )
                AuditService.log_action('admin', current_user.username, 'ADD_POSITION',
                                        f"Added position '{position.title}' to election {election.id}.", request.remote_addr)
                flash(f"Position '{position.title}' added successfully.", 'success')

            elif action == 'add_rule':
                position_id = int(request.form.get('position_id'))
                position = Position.query.filter_by(id=position_id, election_id=election.id).first()
                if not position:
                    raise AdminServiceError('Selected position does not belong to this election.')
                rule = EligibilityRule(
                    election_id=election.id, position_id=position.id,
                    campus=request.form.get('campus', 'ALL'),
                    faculty=request.form.get('faculty', 'ALL'),
                    course=request.form.get('course', 'ALL'),
                    year_of_study=int(request.form.get('year_of_study', 0)),
                    gender=request.form.get('gender', 'ALL'),
                )
                db.session.add(rule)
                db.session.commit()
                AuditService.log_action('admin', current_user.username, 'ADD_ELIGIBILITY_RULE',
                                        f'Added eligibility rule to position {position.id}.', request.remote_addr)
                flash('Eligibility rule added successfully.', 'success')

            else:
                raise AdminServiceError('Unknown election action.')
        except AdminServiceError as exc:
            flash(str(exc), 'danger')
        except (ValueError, TypeError):
            db.session.rollback()
            flash('One or more submitted values are invalid.', 'danger')
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Election configuration failed')
            flash('The requested election change could not be saved.', 'danger')
        return redirect(url_for('admin.election_detail', election_id=election.id))

    return render_template(
        'admin/election_detail.html', election=election,
        positions=Position.query.filter_by(election_id=election.id).order_by(Position.priority_order).all(),
        campuses=current_app.config.get('CAMPUSES', []),
        faculties=current_app.config.get('FACULTIES', [])
    )


@admin_bp.route('/elections/<int:election_id>/position/<int:position_id>/delete', methods=['POST'])
def delete_position(election_id, position_id):
    if current_user.role not in ('super_admin', 'ec_chair', 'ec_commissioner'):
        abort(403)
    pos = Position.query.filter_by(id=position_id, election_id=election_id).first_or_404()
    if pos.election.status in ('closed', 'results_published'):
        flash('Closed elections cannot be modified.', 'danger')
        return redirect(url_for('admin.election_detail', election_id=election_id))
    title = pos.title
    db.session.delete(pos)
    db.session.commit()
    AuditService.log_action('admin', current_user.username, 'DELETE_POSITION',
                            f"Deleted position '{title}' from election {election_id}.", request.remote_addr)
    flash(f"Position '{title}' deleted.", 'info')
    return redirect(url_for('admin.election_detail', election_id=election_id))


@admin_bp.route('/candidates', methods=['GET', 'POST'])
@roles_required('super_admin', 'ec_chair', 'ec_commissioner')
def candidates():
    if request.method == 'POST':
        try:
            election_id = int(request.form.get('election_id'))
            position_id = int(request.form.get('position_id'))
            photo_url = _save_image(request.files.get('photo'), f'candidate_{election_id}')
            symbol_url = _save_image(request.files.get('symbol'), f'symbol_{election_id}')
            candidate = AdminService.register_candidate(
                admin=current_user,
                election_id=election_id,
                position_id=position_id,
                student_id=request.form.get('student_id'),
                full_name=request.form.get('full_name'),
                course=request.form.get('course'),
                campus=request.form.get('campus'),
                symbol_name=request.form.get('symbol_name'),
                manifesto=request.form.get('manifesto'),
                photo_url=photo_url,
                symbol_url=symbol_url,
                status=request.form.get('status', 'pending'),
            )
            AuditService.log_action('admin', current_user.username, 'REGISTER_CANDIDATE',
                                    f"Registered candidate '{candidate.full_name}' for position {candidate.position_id}.", request.remote_addr)
            flash(f"Candidate '{candidate.full_name}' registered successfully.", 'success')
            return redirect(url_for('admin.candidates', election_id=election_id))
        except AdminServiceError as exc:
            flash(str(exc), 'danger')
        except (ValueError, TypeError):
            flash('Please provide valid election and position selections.', 'danger')
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Candidate registration failed')
            flash('The candidate could not be registered.', 'danger')

    selected_election_id = request.args.get('election_id', type=int)
    elections_list = Election.query.order_by(Election.created_at.desc()).all()
    query = Candidate.query
    if selected_election_id:
        query = query.filter_by(election_id=selected_election_id)
    all_candidates = query.order_by(Candidate.created_at.desc()).limit(500).all()
    positions_list = Position.query.order_by(Position.election_id, Position.priority_order).all()
    return render_template(
        'admin/candidates.html', candidates=all_candidates,
        elections=elections_list, positions=positions_list,
        selected_election_id=selected_election_id,
        campuses=current_app.config.get('CAMPUSES', [])
    )


@admin_bp.route('/candidates/<int:candidate_id>/status', methods=['POST'])
def update_candidate_status(candidate_id):
    if current_user.role not in ('super_admin', 'ec_chair', 'ec_commissioner'):
        abort(403)
    candidate = Candidate.query.get_or_404(candidate_id)
    new_status = request.form.get('status')
    reason = request.form.get('disqualification_reason', '').strip()
    if new_status not in ('pending', 'approved', 'disqualified', 'withdrawn'):
        flash('Invalid candidate status.', 'danger')
        return redirect(url_for('admin.candidates', election_id=candidate.election_id))
    if candidate.election.status in ('closed', 'results_published'):
        flash('Candidates cannot be changed after the election is closed.', 'danger')
        return redirect(url_for('admin.candidates', election_id=candidate.election_id))
    candidate.status = new_status
    candidate.disqualification_reason = reason if new_status == 'disqualified' else None
    db.session.commit()
    AuditService.log_action('admin', current_user.username, 'CANDIDATE_STATUS_UPDATE',
                            f'Candidate {candidate.id} status changed to {new_status}.', request.remote_addr)
    flash(f'Candidate {candidate.full_name} status updated.', 'success')
    return redirect(url_for('admin.candidates', election_id=candidate.election_id))


@admin_bp.route('/students')
def students():
    search = request.args.get('q', '').strip()
    campus_filter = request.args.get('campus', '').strip()
    status_filter = request.args.get('status', request.args.get('verification', '')).strip().lower()
    query = Student.query
    if search:
        query = query.filter((Student.student_id.ilike(f'%{search}%')) | (Student.reg_no.ilike(f'%{search}%')) |
                             (Student.full_name.ilike(f'%{search}%')) | (Student.email.ilike(f'%{search}%')))
    if campus_filter:
        query = query.filter(db.func.lower(db.func.trim(Student.campus)) == campus_filter.lower())
    if status_filter == 'verified':
        query = query.filter_by(is_verified=True)
    elif status_filter == 'unverified':
        query = query.filter_by(is_verified=False)

    campus_rows = db.session.query(Student.campus).distinct().order_by(Student.campus).all()
    registry_campuses = {}
    for (campus,) in campus_rows:
        if campus and campus.strip():
            registry_campuses.setdefault(campus.strip().lower(), campus.strip())
    return render_template('admin/students.html', students=query.order_by(Student.created_at.desc()).limit(100).all(),
                           search=search, campus_filter=campus_filter, status_filter=status_filter,
                           registry_campuses=sorted(registry_campuses.values(), key=str.lower),
                           campuses=current_app.config.get('CAMPUSES', []),
                           faculties=current_app.config.get('FACULTIES', []))


@admin_bp.route('/students/register', methods=['POST'])
@roles_required('super_admin', 'ec_chair', 'ec_commissioner')
def register_student():
    try:
        student = AdminService.register_student(
            admin=current_user,
            student_id=request.form.get('student_id'),
            reg_no=request.form.get('reg_no'),
            full_name=request.form.get('full_name'),
            email=request.form.get('email'),
            password=request.form.get('password'),
            campus=request.form.get('campus'),
            faculty=request.form.get('faculty'),
            course=request.form.get('course'),
            year_of_study=request.form.get('year_of_study', 1),
            gender=request.form.get('gender', 'Other'),
            is_verified=request.form.get('is_verified', 'true').lower() == 'true'
        )
        AuditService.log_action('admin', current_user.username, 'REGISTER_STUDENT',
                                f"Registered student '{student.full_name}' ({student.student_id}).", 
                                request.remote_addr)
        flash(f"Student '{student.full_name}' registered successfully.", 'success')
    except AdminServiceError as exc:
        flash(str(exc), 'danger')
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Student registration failed')
        flash('The student could not be registered. Please try again.', 'danger')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/<int:student_id>/verify', methods=['POST'])
@roles_required('super_admin', 'ec_chair', 'ec_commissioner')
def verify_student(student_id):
    try:
        is_verified = request.form.get('is_verified', 'true').lower() == 'true'
        student = AdminService.toggle_student_verification(
            admin=current_user,
            student_id=student_id,
            is_verified=is_verified
        )
        status_text = 'verified' if is_verified else 'unverified'
        AuditService.log_action('admin', current_user.username, 'STUDENT_VERIFICATION_CHANGE',
                                f"Set student {student.student_id} as {status_text}.", 
                                request.remote_addr)
        flash(f"Student {student.full_name} has been {status_text}.", 'success')
    except AdminServiceError as exc:
        flash(str(exc), 'danger')
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Student verification update failed')
        flash('The verification status could not be updated.', 'danger')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/<int:student_id>/toggle-active', methods=['POST'])
@roles_required('super_admin', 'ec_chair')
def toggle_student_active(student_id):
    try:
        is_active = request.form.get('is_active', 'true').lower() == 'true'
        student = AdminService.toggle_student_active_status(
            admin=current_user,
            student_id=student_id,
            is_active=is_active
        )
        status_text = 'activated' if is_active else 'deactivated'
        AuditService.log_action('admin', current_user.username, 'STUDENT_ACCOUNT_STATUS_CHANGE',
                                f"Student {student.student_id} account {status_text}.", 
                                request.remote_addr)
        flash(f"Student {student.full_name}'s account has been {status_text}.", 'success')
    except AdminServiceError as exc:
        flash(str(exc), 'danger')
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Student account status update failed')
        flash('The account status could not be updated.', 'danger')
    return redirect(url_for('admin.students'))


@admin_bp.route('/audit-logs')
def audit_logs():
    action_filter = request.args.get('action', '')
    user_type_filter = request.args.get('user_type', '')
    query = AuditLog.query
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f'%{action_filter}%'))
    if user_type_filter:
        query = query.filter_by(user_type=user_type_filter)
    return render_template('admin/audit_logs.html', logs=query.order_by(AuditLog.created_at.desc()).limit(200).all(),
                           action_filter=action_filter, user_type_filter=user_type_filter)
