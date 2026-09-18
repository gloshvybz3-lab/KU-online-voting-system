from models import db, Notification, utc_now

class NotificationService:
    @staticmethod
    def create_notification(title, message, target_group='all', category='announcement', is_pinned=False, created_by=None):
        """Creates a system announcement / notification."""
        try:
            notif = Notification(
                title=title,
                message=message,
                target_group=target_group,
                category=category,
                is_pinned=is_pinned,
                created_by=created_by
            )
            db.session.add(notif)
            db.session.commit()
            return notif
        except Exception as e:
            db.session.rollback()
            print(f"[NotificationService Error] Failed to create notification: {e}")
            return None

    @staticmethod
    def send_vote_confirmation(student_email, student_name, election_title, receipt_token):
        """
        Sends/logs an email/SMS confirmation stub to the student with their receipt token.
        Does NOT mention candidate choices to preserve ballot secrecy.
        """
        email_body = f"""
Dear {student_name},

Your vote in the '{election_title}' has been successfully recorded by the Kampala University Electoral Commission.

OFFICIAL PARTICIPATION RECEIPT TOKEN:
=======================================
{receipt_token}
=======================================

Timestamp: {utc_now().strftime('%Y-%m-%d %H:%M:%S UTC')}

This token proves your active participation in this election. Due to Kampala University's strict ballot secrecy architecture, your specific voting selections are completely decoupled and anonymous.

Thank you for exercising your democratic right as a Kampala University student.

Kampala University Electoral Commission
"In God We Trust, Knowledge is Power"
"""
        # In a production environment with SMTP/Twilio credentials, send actual dispatch here.
        # Print simulated dispatch to console/logs:
        print(f"--- [MOCK EMAIL DISPATCH to {student_email}] ---")
        print(email_body)
        print("-------------------------------------------------")
        return True

    @staticmethod
    def send_election_broadcast(election, status_change):
        """Sends broadcast alerts when an election opens or closes."""
        title = f"Election Update: {election.title}"
        if status_change == 'opened':
            message = f"Voting is now officially OPEN for '{election.title}'. Eligible students can cast their ballots until {election.end_time.strftime('%Y-%m-%d %H:%M UTC')}."
            category = 'election_open'
        elif status_change == 'closed':
            message = f"Voting is now CLOSED for '{election.title}'. The Electoral Commission is compiling the certified returns."
            category = 'election_close'
        else:
            message = f"Status update for '{election.title}': {status_change}"
            category = 'announcement'

        return NotificationService.create_notification(
            title=title,
            message=message,
            target_group='all',
            category=category,
            is_pinned=True
        )
