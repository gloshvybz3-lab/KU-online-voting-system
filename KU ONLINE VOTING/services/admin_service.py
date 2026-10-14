"""Transactional application services for Electoral Commission administration."""
from datetime import datetime
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models import db, Election, Position, Candidate, utc_now


class AdminServiceError(ValueError):
    pass


class AdminService:
    ALLOWED_ELECTION_STATUSES = {"draft", "scheduled", "active"}
    ALLOWED_CANDIDATE_STATUSES = {"pending", "approved"}

    @staticmethod
    def _require_admin_role(admin, allowed_roles):
        if not admin or not getattr(admin, "is_authenticated", False):
            raise AdminServiceError("Authentication is required.")
        if not getattr(admin, "is_admin", False):
            raise AdminServiceError("Administrator access is required.")
        if getattr(admin, "role", None) not in allowed_roles:
            raise AdminServiceError("You do not have permission to perform this action.")

    @staticmethod
    def create_election(*, admin, title, description, academic_year, start_time, end_time, status="scheduled"):
        AdminService._require_admin_role(admin, {"super_admin", "ec_chair"})
        title = (title or "").strip()
        academic_year = (academic_year or "").strip()
        description = (description or "").strip()
        if not title:
            raise AdminServiceError("Election title is required.")
        if len(title) > 200:
            raise AdminServiceError("Election title must not exceed 200 characters.")
        if not academic_year:
            raise AdminServiceError("Academic year is required.")
        if status not in AdminService.ALLOWED_ELECTION_STATUSES:
            raise AdminServiceError("Invalid election status.")
        if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
            raise AdminServiceError("Valid election dates are required.")
        if end_time <= start_time:
            raise AdminServiceError("Election end time must be after the start time.")

        # Prevent accidental duplicate election creation while allowing multiple
        # different elections in the same academic year.
        duplicate = Election.query.filter(
            db.func.lower(Election.title) == title.lower(),
            Election.academic_year == academic_year,
        ).first()
        if duplicate:
            raise AdminServiceError("An election with this title already exists for that academic year.")

        election = Election(
            title=title,
            description=description or None,
            academic_year=academic_year,
            start_time=start_time,
            end_time=end_time,
            status=status,
            created_by=admin.id,
        )
        try:
            db.session.add(election)
            db.session.commit()
            return election
        except IntegrityError as exc:
            db.session.rollback()
            raise AdminServiceError("The election could not be created because it conflicts with existing data.") from exc
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise AdminServiceError("The election could not be saved. Please try again.") from exc

    @staticmethod
    def add_position(*, admin, election_id, title, description, max_selections=1, priority_order=1):
        AdminService._require_admin_role(admin, {"super_admin", "ec_chair", "ec_commissioner"})
        election = db.session.get(Election, election_id)
        if not election:
            raise AdminServiceError("Election not found.")
        if election.status in {"closed", "results_published"}:
            raise AdminServiceError("Positions cannot be changed after the election is closed.")
        title = (title or "").strip()
        if not title:
            raise AdminServiceError("Position title is required.")
        try:
            max_selections = int(max_selections)
            priority_order = int(priority_order)
        except (TypeError, ValueError) as exc:
            raise AdminServiceError("Selection and order values must be numbers.") from exc
        if not 1 <= max_selections <= 20:
            raise AdminServiceError("Maximum selections must be between 1 and 20.")
        if priority_order < 1:
            raise AdminServiceError("Position order must be at least 1.")

        duplicate = Position.query.filter_by(election_id=election_id).filter(
            db.func.lower(Position.title) == title.lower()
        ).first()
        if duplicate:
            raise AdminServiceError("That position already exists in this election.")

        position = Position(
            election_id=election.id,
            title=title,
            description=(description or "").strip() or None,
            max_selections=max_selections,
            priority_order=priority_order,
        )
        try:
            db.session.add(position)
            db.session.commit()
            return position
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise AdminServiceError("The position could not be saved.") from exc

    @staticmethod
    def register_candidate(*, admin, election_id, position_id, full_name, course, campus,
                            symbol_name=None, manifesto=None, photo_url=None, symbol_url=None,
                            student_id=None, status="pending"):
        AdminService._require_admin_role(admin, {"super_admin", "ec_chair", "ec_commissioner"})
        election = db.session.get(Election, election_id)
        if not election:
            raise AdminServiceError("Election not found.")
        if election.status in {"closed", "results_published"}:
            raise AdminServiceError("Candidates cannot be added to a closed election.")

        # Critical integrity check: a position ID from another election must never
        # be accepted merely because it exists.
        position = Position.query.filter_by(id=position_id, election_id=election.id, is_active=True).first()
        if not position:
            raise AdminServiceError("The selected position does not belong to this election.")

        full_name = (full_name or "").strip()
        course = (course or "").strip()
        campus = (campus or "").strip()
        if not full_name or not course or not campus:
            raise AdminServiceError("Candidate name, course and campus are required.")
        if status not in AdminService.ALLOWED_CANDIDATE_STATUSES:
            raise AdminServiceError("Invalid candidate screening status.")

        duplicate = Candidate.query.filter_by(election_id=election.id, position_id=position.id).filter(
            db.func.lower(Candidate.full_name) == full_name.lower()
        ).first()
        if duplicate:
            raise AdminServiceError("That candidate is already registered for this position.")

        candidate = Candidate(
            election_id=election.id,
            position_id=position.id,
            student_id=(student_id or "").strip() or None,
            full_name=full_name,
            course=course,
            campus=campus,
            symbol_name=(symbol_name or "").strip() or None,
            manifesto=(manifesto or "").strip() or None,
            photo_url=photo_url,
            symbol_url=symbol_url,
            status=status,
        )
        try:
            db.session.add(candidate)
            db.session.commit()
            return candidate
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise AdminServiceError("The candidate could not be saved.") from exc
