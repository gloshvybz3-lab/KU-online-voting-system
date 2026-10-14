import uuid
import random
import hashlib
from datetime import datetime
from sqlalchemy import func
from models import (
    db, Election, Position, Candidate, EligibilityRule,
    VoterParticipation, Vote, Student, utc_now
)
from services.audit_service import AuditService
from services.notification_service import NotificationService

class ElectionService:

    @staticmethod
    def is_student_eligible_for_position(student, position):
        """
        Determines if a student voter meets the eligibility criteria for a given position.
        If no rules exist, the position is open to all students by default.
        If rules exist, matching ANY rule grants eligibility.
        """
        if not position.is_active:
            return False

        rules = EligibilityRule.query.filter_by(position_id=position.id).all()
        if not rules:
            return True

        for rule in rules:
            campus_match = (rule.campus == 'ALL' or rule.campus.strip().lower() == student.campus.strip().lower())
            faculty_match = (rule.faculty == 'ALL' or rule.faculty.strip().lower() == student.faculty.strip().lower())
            course_match = (rule.course == 'ALL' or rule.course.strip().lower() == student.course.strip().lower())
            year_match = (rule.year_of_study == 0 or rule.year_of_study == student.year_of_study)
            gender_match = (rule.gender == 'ALL' or rule.gender.strip().lower() == student.gender.strip().lower())

            if campus_match and faculty_match and course_match and year_match and gender_match:
                return True

        return False

    @staticmethod
    def get_eligible_positions_for_student(student, election_id):
        """
        Retrieves all active positions in the election that the given student is eligible to vote for,
        populated with their approved candidates.
        """
        election = db.session.get(Election, election_id)
        if not election:
            return []

        all_positions = Position.query.filter_by(election_id=election_id, is_active=True).order_by(Position.priority_order).all()
        eligible_positions = []

        for pos in all_positions:
            if ElectionService.is_student_eligible_for_position(student, pos):
                # Attach only approved candidates
                approved_candidates = [c for c in pos.candidates if c.status == 'approved']
                pos.approved_candidates = approved_candidates
                eligible_positions.append(pos)

        return eligible_positions

    @staticmethod
    def has_student_voted(student_id, election_id):
        """Checks if a student has already cast a ballot in the specified election."""
        return VoterParticipation.query.filter_by(
            election_id=election_id,
            student_id=student_id
        ).first() is not None

    @staticmethod
    def cast_ballot(student, election, choices, ip_address=None):
        """
        Cast student ballot with strict adherence to ballot secrecy.
        
        choices format: dict of {position_id: candidate_id or None (for Abstain)}
        
        Guarantees:
        1. Double-voting check before anything.
        2. Strict validation that student is eligible for every chosen position.
        3. Table A (voter_participation) records participation with receipt hash.
        4. Table B (votes) records anonymous ballots with ZERO student identifier.
        5. Shuffles vote records before insert to prevent order-based correlation.
        6. Atomically commits in a single transaction.
        """
        # 1. Verify election is open
        if not election.is_open():
            return False, None, "This election is currently closed or not active for voting."

        # 2. Check double voting
        if ElectionService.has_student_voted(student.id, election.id):
            return False, None, "Double voting detected: You have already cast your ballot in this election."

        # 3. Verify eligible positions
        eligible_positions = ElectionService.get_eligible_positions_for_student(student, election.id)
        eligible_pos_ids = {pos.id for pos in eligible_positions}

        for pos_id_str, cand_id in choices.items():
            pos_id = int(pos_id_str)
            if pos_id not in eligible_pos_ids:
                return False, None, f"Unauthorized: You are not eligible to vote for position ID {pos_id}."

            # Verify candidate is valid for position (if not abstaining)
            if cand_id is not None:
                cand_id = int(cand_id)
                cand = Candidate.query.filter_by(id=cand_id, position_id=pos_id, status='approved').first()
                if not cand:
                    return False, None, f"Invalid or disqualified candidate selected for position ID {pos_id}."

        # 4. Generate verifiable participation receipt token
        entropy = f"{student.student_id}:{election.id}:{uuid.uuid4().hex}:{utc_now().timestamp()}"
        receipt_token = "KU-" + hashlib.sha256(entropy.encode()).hexdigest()[:16].upper()
        ip_hash = AuditService.hash_ip(ip_address)

        try:
            # 5. Insert Table A: Voter Participation (prevents double voting)
            participation = VoterParticipation(
                election_id=election.id,
                student_id=student.id,
                receipt_token=receipt_token,
                voted_at=utc_now(),
                ip_address_hash=ip_hash
            )
            db.session.add(participation)

            # 6. Prepare Table B: Anonymous Votes (NO voter reference, NO receipt token)
            vote_records = []
            for pos_id_str, cand_id in choices.items():
                pos_id = int(pos_id_str)
                vote_obj = Vote(
                    election_id=election.id,
                    position_id=pos_id,
                    candidate_id=int(cand_id) if cand_id is not None else None,
                    created_at=utc_now()
                )
                vote_records.append(vote_obj)

            # Shuffle order to protect against positional / batch correlation
            random.shuffle(vote_records)
            db.session.add_all(vote_records)

            # Commit the atomic transaction
            db.session.commit()

            # 7. Audit log event (Records that voter cast a vote, but NEVER logs vote selections)
            AuditService.log_action(
                user_type='student',
                user_identifier=student.student_id,
                action='VOTE_CAST_SUCCESS',
                details=f"Ballot cast in Election ID {election.id} ({election.title}). Receipt: {receipt_token}",
                ip_address=ip_hash
            )

            # 8. Dispatch notification receipt (non-blocking)
            NotificationService.send_vote_confirmation(
                student_email=student.email,
                student_name=student.full_name,
                election_title=election.title,
                receipt_token=receipt_token
            )

            return True, receipt_token, "Your vote has been cast successfully."

        except Exception as e:
            db.session.rollback()
            print(f"[ElectionService Error] Failed to cast ballot: {e}")
            return False, None, "A database error occurred while submitting your vote. Please try again."

    @staticmethod
    def get_election_results(election_id, allow_unapproved=False):
        """
        Compiles vote counts and turnout statistics for an election.
        If allow_unapproved is False (e.g. for students/public), only returns results if election.status == 'results_published'.
        """
        election = db.session.get(Election, election_id)
        if not election:
            return None

        if not allow_unapproved and election.status != 'results_published':
            return None

        # Gather positions and vote tallies
        positions_data = []
        positions = Position.query.filter_by(election_id=election_id).order_by(Position.priority_order).all()

        for pos in positions:
            # Total votes for this position (including abstains)
            total_position_votes = Vote.query.filter_by(position_id=pos.id).count()

            # Abstain votes
            abstain_count = Vote.query.filter_by(position_id=pos.id, candidate_id=None).count()

            candidates_data = []
            max_votes = -1
            winners = []

            for cand in pos.candidates:
                votes_count = Vote.query.filter_by(position_id=pos.id, candidate_id=cand.id).count()
                percentage = round((votes_count / total_position_votes * 100), 2) if total_position_votes > 0 else 0.0

                cand_dict = {
                    'id': cand.id,
                    'full_name': cand.full_name,
                    'course': cand.course,
                    'campus': cand.campus,
                    'photo_url': cand.photo_url,
                    'symbol_name': cand.symbol_name,
                    'symbol_url': cand.symbol_url,
                    'status': cand.status,
                    'votes': votes_count,
                    'percentage': percentage,
                    'is_winner': False
                }
                candidates_data.append(cand_dict)

                if votes_count > max_votes and votes_count > 0:
                    max_votes = votes_count

            # Mark winners (could be tied)
            if max_votes > 0:
                for c in candidates_data:
                    if c['votes'] == max_votes:
                        c['is_winner'] = True

            # Sort candidates by votes descending
            candidates_data.sort(key=lambda x: x['votes'], reverse=True)

            abstain_percentage = round((abstain_count / total_position_votes * 100), 2) if total_position_votes > 0 else 0.0

            positions_data.append({
                'position_id': pos.id,
                'title': pos.title,
                'description': pos.description,
                'total_votes': total_position_votes,
                'abstain_count': abstain_count,
                'abstain_percentage': abstain_percentage,
                'candidates': candidates_data
            })

        # Turnout Statistics
        total_registered_students = Student.query.filter_by(is_active=True).count()
        total_voters_participated = VoterParticipation.query.filter_by(election_id=election_id).count()
        overall_turnout_pct = round((total_voters_participated / total_registered_students * 100), 2) if total_registered_students > 0 else 0.0

        # Turnout by Campus
        campus_turnout = []
        campus_rows = db.session.query(
            Student.campus,
            func.count(VoterParticipation.id)
        ).join(
            VoterParticipation,
            (VoterParticipation.student_id == Student.id) & (VoterParticipation.election_id == election_id)
        ).group_by(Student.campus).all()

        voted_by_campus_map = {c[0]: c[1] for c in campus_rows}
        all_campus_counts = db.session.query(Student.campus, func.count(Student.id)).filter(Student.is_active == True).group_by(Student.campus).all()

        for campus_name, total_students in all_campus_counts:
            voted_count = voted_by_campus_map.get(campus_name, 0)
            pct = round((voted_count / total_students * 100), 2) if total_students > 0 else 0.0
            campus_turnout.append({
                'campus': campus_name,
                'voted': voted_count,
                'total': total_students,
                'percentage': pct
            })

        # Turnout by Faculty
        faculty_turnout = []
        faculty_rows = db.session.query(
            Student.faculty,
            func.count(VoterParticipation.id)
        ).join(
            VoterParticipation,
            (VoterParticipation.student_id == Student.id) & (VoterParticipation.election_id == election_id)
        ).group_by(Student.faculty).all()

        voted_by_faculty_map = {f[0]: f[1] for f in faculty_rows}
        all_faculty_counts = db.session.query(Student.faculty, func.count(Student.id)).filter(Student.is_active == True).group_by(Student.faculty).all()

        for faculty_name, total_students in all_faculty_counts:
            voted_count = voted_by_faculty_map.get(faculty_name, 0)
            pct = round((voted_count / total_students * 100), 2) if total_students > 0 else 0.0
            faculty_turnout.append({
                'faculty': faculty_name,
                'voted': voted_count,
                'total': total_students,
                'percentage': pct
            })

        return {
            'election': {
                'id': election.id,
                'title': election.title,
                'academic_year': election.academic_year,
                'status': election.status,
                'start_time': election.start_time,
                'end_time': election.end_time,
                'results_approved_at': election.results_approved_at,
            },
            'turnout': {
                'total_registered': total_registered_students,
                'total_voted': total_voters_participated,
                'overall_percentage': overall_turnout_pct,
                'by_campus': campus_turnout,
                'by_faculty': faculty_turnout
            },
            'positions': positions_data
        }

    @staticmethod
    def auto_update_election_statuses():
        """
        Cron / scheduled periodic helper to update statuses from 'scheduled' to 'active'
        and from 'active' to 'closed' based on UTC timestamp.
        """
        now = utc_now()
        # Scheduled to active
        scheduled_elections = Election.query.filter(
            Election.status == 'scheduled',
            Election.start_time <= now
        ).all()
        for el in scheduled_elections:
            el.status = 'active'
            NotificationService.send_election_broadcast(el, 'opened')

        # Active to closed
        active_elections = Election.query.filter(
            Election.status == 'active',
            Election.end_time < now
        ).all()
        for el in active_elections:
            el.status = 'closed'
            NotificationService.send_election_broadcast(el, 'closed')

        if scheduled_elections or active_elections:
            db.session.commit()
