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
    def add_position(*, admin, election_id, title, description, max_selections=1, priority_order=None):
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
            priority_order = int(priority_order) if priority_order is not None else None
        except (TypeError, ValueError) as exc:
            raise AdminServiceError("Selection and order values must be numbers.") from exc
        if not 1 <= max_selections <= 20:
            raise AdminServiceError("Maximum selections must be between 1 and 20.")
        if priority_order is None:
            highest_order = db.session.query(db.func.max(Position.priority_order)).filter_by(
                election_id=election_id
            ).scalar()
            priority_order = (highest_order or 0) + 1
        elif priority_order < 1:
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

    @staticmethod
    def register_student(*, admin, student_id, reg_no, full_name, email, password, campus, 
                        faculty, course, year_of_study=1, gender='Other', is_verified=True):
        """Register a new student voter account."""
        from models import Student, UniversityRecord
        AdminService._require_admin_role(admin, {"super_admin", "ec_chair", "ec_commissioner"})
        
        # Validate required fields
        student_id = (student_id or "").strip().upper()
        reg_no = (reg_no or "").strip()
        full_name = (full_name or "").strip()
        email = (email or "").strip().lower()
        password = (password or "").strip()
        campus = (campus or "").strip()
        faculty = (faculty or "").strip()
        course = (course or "").strip()
        
        if not all([student_id, reg_no, full_name, email, password, campus, faculty, course]):
            raise AdminServiceError("All required fields must be provided.")
        
        # Validate student ID format
        if not student_id.startswith("KU"):
            raise AdminServiceError("Student ID must start with 'KU' (e.g., KU12345).")
        
        if len(student_id) < 4:
            raise AdminServiceError("Student ID must be at least 4 characters long (KU + digits).")
        
        if len(password) < 6:
            raise AdminServiceError("Password must be at least 6 characters long.")

        # Use registrar attributes when the student is present in the authoritative roster.
        registrar_matches = UniversityRecord.query.filter(
            (db.func.lower(UniversityRecord.student_id) == student_id.lower()) |
            (db.func.lower(UniversityRecord.reg_no) == reg_no.lower())
        ).all()
        if registrar_matches:
            if (
                len(registrar_matches) != 1 or
                registrar_matches[0].student_id.lower() != student_id.lower() or
                registrar_matches[0].reg_no.lower() != reg_no.lower()
            ):
                raise AdminServiceError("Student ID and registration number must match the same registrar record.")
            registrar_record = registrar_matches[0]
            if not registrar_record.is_registered_student:
                raise AdminServiceError("This student is not eligible for voter registration in the registrar records.")

            full_name = registrar_record.full_name
            email = registrar_record.email.lower()
            campus = registrar_record.campus
            faculty = registrar_record.faculty
            course = registrar_record.course
            year_of_study = registrar_record.year_of_study
            gender = registrar_record.gender
        
        # Check for duplicates
        if Student.query.filter(
            (Student.student_id == student_id) | 
            (Student.reg_no == reg_no) | 
            (Student.email == email)
        ).first():
            raise AdminServiceError("A student with this Student ID, Reg No, or Email already exists.")
        
        try:
            year_of_study = int(year_of_study)
            if not 1 <= year_of_study <= 7:
                raise ValueError()
        except (TypeError, ValueError) as exc:
            raise AdminServiceError("Year of study must be between 1 and 7.") from exc
        
        student = Student(
            student_id=student_id,
            reg_no=reg_no,
            full_name=full_name,
            email=email,
            campus=campus,
            faculty=faculty,
            course=course,
            year_of_study=year_of_study,
            gender=gender,
            is_verified=is_verified,
            is_active=True
        )
        student.set_password(password)
        
        try:
            db.session.add(student)
            db.session.commit()
            return student
        except IntegrityError as exc:
            db.session.rollback()
            raise AdminServiceError("A student with these details already exists.") from exc
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise AdminServiceError("The student could not be registered. Please try again.") from exc

    @staticmethod
    def toggle_student_verification(*, admin, student_id, is_verified):
        """Verify or unverify a student's voting eligibility."""
        from models import Student
        AdminService._require_admin_role(admin, {"super_admin", "ec_chair", "ec_commissioner"})
        
        student = db.session.get(Student, student_id)
        if not student:
            raise AdminServiceError("Student not found.")
        
        student.is_verified = bool(is_verified)
        student.updated_at = utc_now()
        
        try:
            db.session.commit()
            return student
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise AdminServiceError("The verification status could not be updated.") from exc

    @staticmethod
    def toggle_student_active_status(*, admin, student_id, is_active):
        """Activate or deactivate a student account."""
        from models import Student
        AdminService._require_admin_role(admin, {"super_admin", "ec_chair"})
        
        student = db.session.get(Student, student_id)
        if not student:
            raise AdminServiceError("Student not found.")
        
        student.is_active = bool(is_active)
        student.updated_at = utc_now()
        
        try:
            db.session.commit()
            return student
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise AdminServiceError("The account status could not be updated.") from exc
