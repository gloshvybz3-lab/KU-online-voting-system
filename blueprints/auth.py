import random
import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Student, User
from services.notification_service import send_email_otp

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Mock in-memory OTP store for fast hackathon demo (In production, stored in DB or Redis)
otp_store = {}

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        reg_number = request.form.get('reg_number')
        password = request.form.get('password')
        student = Student.query.filter_by(reg_number=reg_number).first()
        if student and check_password_hash(student.password_hash, password):
            session['user_id'] = student.id
            session['role'] = 'student'
            session['name'] = student.full_name
            flash('Login successful!', 'success')
            return redirect(url_for('voting.elections'))
        flash('Invalid Registration Number or Password.', 'danger')
    return render_template('auth/login.html')

@auth_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['name'] = user.full_name
            flash('Admin authentication successful.', 'success')
            return redirect(url_for('admin.dashboard'))
        flash('Invalid Admin Credentials.', 'danger')
    return render_template('auth/admin_login.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        student = Student.query.filter_by(email=email).first()
        if student:
            otp = f"{random.randint(100000, 999999)}"
            otp_store[email] = {
                'otp': otp,
                'expires': datetime.datetime.now() + datetime.timedelta(minutes=10)
            }
            send_email_otp(email, otp)
            flash('A 6-digit verification code has been sent to your email.', 'info')
            return redirect(url_for('auth.reset_password', email=email))
        else:
            flash('No account found with that email address.', 'danger')
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = request.args.get('email') or request.form.get('email')
    if request.method == 'POST':
        otp_entered = request.form.get('otp')
        new_password = request.form.get('new_password')
        record = otp_store.get(email)
        
        if record and record['otp'] == otp_entered and datetime.datetime.now() < record['expires']:
            student = Student.query.filter_by(email=email).first()
            if student:
                student.password_hash = generate_password_hash(new_password)
                db.session.commit()
                otp_store.pop(email, None)
                flash('Password reset successful! You can now log in.', 'success')
                return redirect(url_for('auth.login'))
        flash('Invalid or expired verification code. Please try again.', 'danger')
    return render_template('auth/reset_password.html', email=email)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        current_pwd = request.form.get('current_password')
        new_pwd = request.form.get('new_password')
        student = Student.query.get(session['user_id'])
        
        if student and check_password_hash(student.password_hash, current_pwd):
            student.password_hash = generate_password_hash(new_pwd)
            db.session.commit()
            flash('Your password has been updated successfully.', 'success')
            return redirect(url_for('voting.elections'))
        flash('Incorrect current password.', 'danger')
    return render_template('auth/change_password.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('main.index'))
