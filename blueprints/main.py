from datetime import datetime
from flask import Blueprint, render_template, request, flash
from models import Election, Notification, FAQ, VoterParticipation
from services.election_service import ElectionService

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Kampala University Online Voting System Homepage."""
    ElectionService.auto_update_election_statuses()

    # Active and upcoming elections
    active_elections = Election.query.filter_by(status='active').order_by(Election.end_time.asc()).all()
    upcoming_elections = Election.query.filter_by(status='scheduled').order_by(Election.start_time.asc()).all()
    recent_published = Election.query.filter_by(status='results_published').order_by(Election.end_time.desc()).limit(3).all()

    # Pinned announcements
    announcements = Notification.query.filter_by(is_pinned=True).order_by(Notification.created_at.desc()).limit(5).all()

    return render_template(
        'index.html',
        active_elections=active_elections,
        upcoming_elections=upcoming_elections,
        recent_published=recent_published,
        announcements=announcements
    )


@main_bp.route('/faq')
def faq():
    """Frequently Asked Questions & Voter Instructions."""
    faqs = FAQ.query.filter_by(is_active=True).order_by(FAQ.priority_order).all()
    return render_template('main/faq.html', faqs=faqs)


@main_bp.route('/announcements')
def announcements():
    """Official Electoral Commission announcements and notices."""
    notifs = Notification.query.order_by(Notification.is_pinned.desc(), Notification.created_at.desc()).all()
    return render_template('main/announcements.html', notifications=notifs)


@main_bp.route('/verify-receipt', methods=['GET', 'POST'])
def verify_receipt():
    """
    Public receipt validator:
    Allows any voter to input their cryptographic receipt token and independently
    verify that their vote was received, timestamped, and stored in the official participation roll.
    Crucially, it verifies participation without revealing any ballot selections.
    """
    verification_result = None
    searched_token = ""

    if request.method == 'POST':
        searched_token = request.form.get('token', '').strip().upper()

        if searched_token:
            vp = VoterParticipation.query.filter_by(receipt_token=searched_token).first()
            if vp:
                verification_result = {
                    'valid': True,
                    'token': vp.receipt_token,
                    'election_title': vp.election.title,
                    'academic_year': vp.election.academic_year,
                    'voted_at': vp.voted_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'status': 'OFFICIALLY RECORDED & VERIFIED'
                }
            else:
                verification_result = {
                    'valid': False,
                    'token': searched_token,
                    'message': 'No recorded vote matches this receipt token. Please ensure it was copied correctly.'
                }

    return render_template('main/verify_receipt.html', result=verification_result, token=searched_token)
