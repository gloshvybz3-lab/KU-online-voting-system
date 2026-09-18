from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

db = SQLAlchemy()

class UniversityRecord(db.Model):
    """
    Authoritative student roster from the University Registrar.
    Used to verify legitimate KU students during registration.
    """
    __tablename__ = 'university_records'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    reg_no = db.Column(db.String(50), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    campus = db.Column(db.String(100), nullable=False, index=True)
    faculty = db.Column(db.String(150), nullable=False, index=True)
    course = db.Column(db.String(150), nullable=False, index=True)
    year_of_study = db.Column(db.Integer, default=1, nullable=False)
    gender = db.Column(db.String(10), default='Other', nullable=False)
    is_registered_student = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f"<UniversityRecord {self.student_id} - {self.full_name}>"


class Student(UserMixin, db.Model):
    """
    Registered and verified student voter account.
    """
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    reg_no = db.Column(db.String(50), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    campus = db.Column(db.String(100), nullable=False, index=True)
    faculty = db.Column(db.String(150), nullable=False, index=True)
    course = db.Column(db.String(150), nullable=False)
    year_of_study = db.Column(db.Integer, default=1, nullable=False)
    gender = db.Column(db.String(10), default='Other', nullable=False)
    is_verified = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    @property
    def is_admin(self):
        return False

    @property
    def is_student(self):
        return True

    def get_id(self):
        return f"student_{self.id}"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Student {self.student_id} - {self.full_name}>"


class Admin(UserMixin, db.Model):
    """
    Electoral Commission members and system administrators.
    """
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='ec_commissioner', nullable=False) 
    # Roles: 'super_admin', 'ec_chair', 'ec_commissioner', 'auditor'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    @property
    def is_admin(self):
        return True

    @property
    def is_student(self):
        return False

    @property
    def can_publish_results(self):
        return self.role in ('super_admin', 'ec_chair')

    @property
    def can_manage_candidates(self):
        return self.role in ('super_admin', 'ec_chair', 'ec_commissioner')

    def get_id(self):
        return f"admin_{self.id}"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Admin {self.username} ({self.role})>"


class Election(db.Model):
    """
    Election event model with start/end schedules and publishing gate.
    """
    __tablename__ = 'elections'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    academic_year = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(30), default='draft', nullable=False)
    # statuses: 'draft', 'scheduled', 'active', 'paused', 'closed', 'results_published'
    results_approved_by = db.Column(db.Integer, db.ForeignKey('admins.id', ondelete='SET NULL'), nullable=True)
    results_approved_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('admins.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    positions = db.relationship('Position', backref='election', cascade='all, delete-orphan', lazy=True, order_by='Position.priority_order')
    candidates = db.relationship('Candidate', backref='election', cascade='all, delete-orphan', lazy=True)
    eligibility_rules = db.relationship('EligibilityRule', backref='election', cascade='all, delete-orphan', lazy=True)
    participations = db.relationship('VoterParticipation', backref='election', cascade='all, delete-orphan', lazy='dynamic')
    votes = db.relationship('Vote', backref='election', cascade='all, delete-orphan', lazy='dynamic')

    def is_open(self):
        """Returns True if election is open right now according to clock and status."""
        now = utc_now()
        if self.status in ('paused', 'closed', 'results_published', 'draft'):
            return False
        return self.start_time <= now <= self.end_time

    def get_effective_status(self):
        """Calculates current dynamic status considering schedule window."""
        now = utc_now()
        if self.status == 'results_published':
            return 'results_published'
        if self.status in ('draft', 'paused'):
            return self.status
        if now < self.start_time:
            return 'scheduled'
        elif self.start_time <= now <= self.end_time:
            return 'active'
        else:
            return 'closed'

    def __repr__(self):
        return f"<Election {self.id}: {self.title} ({self.status})>"


class Position(db.Model):
    """
    Offices contested within an election.
    """
    __tablename__ = 'positions'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    max_selections = db.Column(db.Integer, default=1, nullable=False)
    priority_order = db.Column(db.Integer, default=1, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    candidates = db.relationship('Candidate', backref='position', cascade='all, delete-orphan', lazy=True)
    eligibility_rules = db.relationship('EligibilityRule', backref='position', cascade='all, delete-orphan', lazy=True)
    votes = db.relationship('Vote', backref='position', cascade='all, delete-orphan', lazy='dynamic')

    def __repr__(self):
        return f"<Position {self.id}: {self.title}>"


class Candidate(db.Model):
    """
    Candidates running for election positions.
    """
    __tablename__ = 'candidates'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.String(50), nullable=True)
    full_name = db.Column(db.String(150), nullable=False)
    course = db.Column(db.String(150), nullable=False)
    campus = db.Column(db.String(100), nullable=False)
    photo_url = db.Column(db.String(255), nullable=True)
    symbol_url = db.Column(db.String(255), nullable=True)
    symbol_name = db.Column(db.String(100), nullable=True)
    manifesto = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='approved', nullable=False)
    # statuses: 'pending', 'approved', 'disqualified', 'withdrawn'
    disqualification_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    votes = db.relationship('Vote', backref='candidate', cascade='all, delete-orphan', lazy='dynamic')

    def __repr__(self):
        return f"<Candidate {self.id}: {self.full_name} for Position {self.position_id}>"


class EligibilityRule(db.Model):
    """
    Defines who is allowed to vote for a specific position.
    'ALL' indicates universal eligibility for that dimension.
    """
    __tablename__ = 'eligibility_rules'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False)
    campus = db.Column(db.String(100), default='ALL', nullable=False)
    faculty = db.Column(db.String(150), default='ALL', nullable=False)
    course = db.Column(db.String(150), default='ALL', nullable=False)
    year_of_study = db.Column(db.Integer, default=0, nullable=False) # 0 means all years
    gender = db.Column(db.String(10), default='ALL', nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f"<Rule for Pos {self.position_id}: Campus={self.campus}, Faculty={self.faculty}, Year={self.year_of_study}>"


class VoterParticipation(db.Model):
    """
    TABLE A: Tracks that a student has voted in an election to prevent double voting.
    CRITICAL BALLOT SECRECY: Does NOT contain any reference to candidate choice.
    """
    __tablename__ = 'voter_participation'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    receipt_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    voted_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    ip_address_hash = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    __table_args__ = (
        db.UniqueConstraint('election_id', 'student_id', name='uq_voter_election'),
    )

    student = db.relationship('Student', backref=db.backref('participations', lazy=True))

    def __repr__(self):
        return f"<VoterParticipation Student {self.student_id} in Election {self.election_id}>"


class Vote(db.Model):
    """
    TABLE B: Anonymous ballot choices.
    CRITICAL BALLOT SECRECY:
    - NO student_id
    - NO receipt_token
    - NO user foreign key or join path back to the voter
    - Fully anonymous
    """
    __tablename__ = 'votes'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id', ondelete='CASCADE'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f"<Vote Election {self.election_id} Pos {self.position_id} Cand {self.candidate_id}>"


class Notification(db.Model):
    """
    System announcements, broadcast messages, and notifications.
    """
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    target_group = db.Column(db.String(20), default='all', nullable=False)
    category = db.Column(db.String(30), default='announcement', nullable=False)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('admins.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f"<Notification {self.id}: {self.title}>"


class AuditLog(db.Model):
    """
    Security audit trail of user and administrator actions.
    """
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(20), nullable=False) # 'student', 'admin', 'system'
    user_identifier = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f"<AuditLog {self.created_at} [{self.user_identifier}]: {self.action}>"


class FAQ(db.Model):
    """
    Voter assistance questions and answers.
    """
    __tablename__ = 'faqs'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), default='General', nullable=False)
    question = db.Column(db.String(255), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    priority_order = db.Column(db.Integer, default=1, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f"<FAQ {self.id}: {self.question}>"
