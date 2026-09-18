from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from models import db, Student, Admin, UniversityRecord, utc_now
from services.audit_service import AuditService

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def student_login():
    """Student voter login via Student ID or University Email."""
    if current_user.is_authenticated:
        if current_user.is_student:
            return redirect(url_for('voting.list_elections'))
        elif current_user.is_admin:
            return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not identifier or not password:
            flash('Please enter both your Student ID/Email and password.', 'warning')
            return render_template('auth/login.html', identifier=identifier)

        # Look up student by student_id or email
        student = Student.query.filter(
            (Student.student_id == identifier) | (Student.email.ilike(identifier))
        ).first()

        if student and student.check_password(password):
            if not student.is_active:
                flash('Your account has been deactivated. Please contact the Electoral Commission.', 'danger')
                return render_template('auth/login.html', identifier=identifier)

            student.last_login = utc_now()
            db.session.commit()

            login_user(student, remember=remember)
            session.permanent = True

            AuditService.log_action(
                user_type='student',
                user_identifier=student.student_id,
                action='STUDENT_LOGIN',
                details=f"Successful login for {student.full_name} ({student.campus})",
                ip_address=request.remote_addr
            )

            flash(f'Welcome, {student.full_name}! You are logged in to Kampala University Online Voting System.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('voting.list_elections'))

        AuditService.log_action(
            user_type='student',
            user_identifier=identifier,
            action='LOGIN_FAILED',
            details='Invalid credentials supplied',
            ip_address=request.remote_addr
        )
        flash('Invalid Student ID / Email or password. Please verify and try again.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def student_register():
    """
    Student registration with instant verification against authoritative University Records.
    Ensures only legitimate KU students can create a voter profile.
    """
    if current_user.is_authenticated:
        return redirect(url_for('voting.list_elections'))

    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        reg_no = request.form.get('reg_no', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not student_id or not reg_no or not password:
            flash('All fields are required for registration.', 'warning')
            return render_template('auth/register.html', student_id=student_id, reg_no=reg_no)

        if password != confirm_password:
            flash('Passwords do not match. Please re-enter.', 'danger')
            return render_template('auth/register.html', student_id=student_id, reg_no=reg_no)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html', student_id=student_id, reg_no=reg_no)

        # Check if already registered
        existing_student = Student.query.filter(
            (Student.student_id == student_id) | (Student.reg_no == reg_no)
        ).first()

        if existing_student:
            flash('An account with this Student ID or Reg No already exists. Please log in.', 'info')
            return redirect(url_for('auth.student_login'))

        # Verify against authoritative university records
        uni_record = UniversityRecord.query.filter(
            (UniversityRecord.student_id.ilike(student_id)) & 
            (UniversityRecord.reg_no.ilike(reg_no)) &
            (UniversityRecord.is_registered_student == True)
        ).first()

        if not uni_record:
            flash('Verification failed: No matching student record found in the Kampala University official registrar database. Please check your Student ID and Registration Number or contact Academic Registrar.', 'danger')
            return render_template('auth/register.html', student_id=student_id, reg_no=reg_no)

        # Create verified student record
        new_student = Student(
            student_id=uni_record.student_id,
            reg_no=uni_record.reg_no,
            full_name=uni_record.full_name,
            email=uni_record.email,
            campus=uni_record.campus,
            faculty=uni_record.faculty,
            course=uni_record.course,
            year_of_study=uni_record.year_of_study,
            gender=uni_record.gender,
            is_verified=True,
            is_active=True
        )
        new_student.set_password(password)

        try:
            db.session.add(new_student)
            db.session.commit()

            AuditService.log_action(
                user_type='student',
                user_identifier=new_student.student_id,
                action='STUDENT_REGISTER_SUCCESS',
                details=f"Verified & registered student: {new_student.full_name}, Campus: {new_student.campus}",
                ip_address=request.remote_addr
            )

            flash('Account verified and created successfully! You can now log in to vote.', 'success')
            return redirect(url_for('auth.student_login'))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred during account creation. Please try again.', 'danger')

    return render_template('auth/register.html')


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Dedicated login for Electoral Commission (EC) and System Administrators."""
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        if not identifier or not password:
            flash('Please enter your username/email and password.', 'warning')
            return render_template('auth/admin_login.html', identifier=identifier)

        admin = Admin.query.filter(
            (Admin.username == identifier) | (Admin.email.ilike(identifier))
        ).first()

        if admin and admin.check_password(password):
            if not admin.is_active:
                flash('This administrator account is disabled.', 'danger')
                return render_template('auth/admin_login.html', identifier=identifier)

            admin.last_login = utc_now()
            db.session.commit()

            login_user(admin)
            session.permanent = True

            AuditService.log_action(
                user_type='admin',
                user_identifier=admin.username,
                action='ADMIN_LOGIN',
                details=f"Admin {admin.full_name} logged in with role {admin.role}",
                ip_address=request.remote_addr
            )

            flash(f'Welcome back, {admin.full_name} ({admin.role.replace("_", " ").title()})', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin.dashboard'))

        AuditService.log_action(
            user_type='admin',
            user_identifier=identifier,
            action='ADMIN_LOGIN_FAILED',
            details='Invalid admin credentials supplied',
            ip_address=request.remote_addr
        )
        flash('Invalid administrator credentials.', 'danger')

    return render_template('auth/admin_login.html')


@auth_bp.route('/logout')
def logout():
    """Log out student or admin."""
    if current_user.is_authenticated:
        user_type = 'admin' if current_user.is_admin else 'student'
        ident = current_user.username if current_user.is_admin else current_user.student_id

        AuditService.log_action(
            user_type=user_type,
            user_identifier=ident,
            action='LOGOUT',
            ip_address=request.remote_addr
        )
        logout_user()

    session.clear()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('main.index'))
