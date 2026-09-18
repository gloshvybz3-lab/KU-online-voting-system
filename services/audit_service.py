import hashlib
from models import db, AuditLog

class AuditService:
    @staticmethod
    def log_action(user_type, user_identifier, action, details=None, ip_address=None):
        """
        Records an audit event in the immutable audit log table.
        NOTE: user_identifier is student ID or admin username.
        NEVER logs or correlates vote selections.
        """
        try:
            log_entry = AuditLog(
                user_type=user_type,
                user_identifier=str(user_identifier),
                action=action,
                details=details,
                ip_address=ip_address
            )
            db.session.add(log_entry)
            db.session.commit()
            return log_entry
        except Exception as e:
            db.session.rollback()
            # Fail silently to avoid breaking the core transaction, but print to server log
            print(f"[AuditService Error] Failed to write audit log: {e}")
            return None

    @staticmethod
    def hash_ip(ip_address):
        """Hashes an IP address for privacy-preserving audit logs."""
        if not ip_address:
            return None
        return hashlib.sha256(ip_address.encode('utf-8')).hexdigest()[:16]
