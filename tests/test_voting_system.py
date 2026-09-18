import unittest
from datetime import datetime, timedelta, timezone
from app import create_app
from config import TestingConfig
from models import (
    db, UniversityRecord, Student, Admin, Election, Position,
    Candidate, EligibilityRule, VoterParticipation, Vote, utc_now
)
from services.election_service import ElectionService

class TestVotingSystem(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Seed minimal test data
        self.now = utc_now()

        # Admin
        self.admin = Admin(
            username="test_admin",
            email="admin@ku.ac.ug",
            full_name="Test Admin",
            role="ec_chair"
        )
        self.admin.set_password("Admin@123")
        db.session.add(self.admin)

        # University Records
        self.ur1 = UniversityRecord(
            student_id="KU/TEST/001",
            reg_no="24/KU/T01/UG",
            full_name="Mukasa John",
            email="john@ku.ac.ug",
            campus="Ggaba (Main Campus)",
            faculty="Faculty of Computer Science and Information Technology",
            course="Bachelor of Information Technology",
            year_of_study=2,
            gender="Male"
        )
        self.ur2 = UniversityRecord(
            student_id="KU/TEST/002",
            reg_no="24/KU/T02/UG",
            full_name="Namubiru Mary",
            email="mary@ku.ac.ug",
            campus="Luweero Campus",
            faculty="Faculty of Education",
            course="Bachelor of Education",
            year_of_study=1,
            gender="Female"
        )
        db.session.add_all([self.ur1, self.ur2])

        # Registered Students
        self.s1 = Student(
            student_id=self.ur1.student_id,
            reg_no=self.ur1.reg_no,
            full_name=self.ur1.full_name,
            email=self.ur1.email,
            campus=self.ur1.campus,
            faculty=self.ur1.faculty,
            course=self.ur1.course,
            year_of_study=self.ur1.year_of_study,
            gender=self.ur1.gender,
            is_verified=True,
            is_active=True
        )
        self.s1.set_password("Student@123")

        self.s2 = Student(
            student_id=self.ur2.student_id,
            reg_no=self.ur2.reg_no,
            full_name=self.ur2.full_name,
            email=self.ur2.email,
            campus=self.ur2.campus,
            faculty=self.ur2.faculty,
            course=self.ur2.course,
            year_of_study=self.ur2.year_of_study,
            gender=self.ur2.gender,
            is_verified=True,
            is_active=True
        )
        self.s2.set_password("Student@123")
        db.session.add_all([self.s1, self.s2])

        # Active Election
        self.election = Election(
            title="Guild Elections 2026",
            academic_year="2025/2026",
            start_time=self.now - timedelta(hours=1),
            end_time=self.now + timedelta(hours=10),
            status="active",
            created_by=self.admin.id
        )
        db.session.add(self.election)
        db.session.commit()

        # Position 1: Guild President (Universal)
        self.pos_president = Position(
            election_id=self.election.id,
            title="Guild President",
            priority_order=1
        )
        db.session.add(self.pos_president)
        db.session.commit()
        db.session.add(EligibilityRule(election_id=self.election.id, position_id=self.pos_president.id, campus="ALL", faculty="ALL", course="ALL", year_of_study=0, gender="ALL"))

        # Position 2: Ggaba Campus Rep (Ggaba Only)
        self.pos_ggaba = Position(
            election_id=self.election.id,
            title="Ggaba Campus Representative",
            priority_order=2
        )
        db.session.add(self.pos_ggaba)
        db.session.commit()
        db.session.add(EligibilityRule(election_id=self.election.id, position_id=self.pos_ggaba.id, campus="Ggaba (Main Campus)", faculty="ALL", course="ALL", year_of_study=0, gender="ALL"))

        # Position 3: Female Affairs (Female Only)
        self.pos_female = Position(
            election_id=self.election.id,
            title="Female Affairs Minister",
            priority_order=3
        )
        db.session.add(self.pos_female)
        db.session.commit()
        db.session.add(EligibilityRule(election_id=self.election.id, position_id=self.pos_female.id, campus="ALL", faculty="ALL", course="ALL", year_of_study=0, gender="Female"))

        # Candidates
        self.cand_pres1 = Candidate(election_id=self.election.id, position_id=self.pos_president.id, full_name="Candidate A", course="BBA", campus="Ggaba", status="approved")
        self.cand_pres2 = Candidate(election_id=self.election.id, position_id=self.pos_president.id, full_name="Candidate B", course="BIT", campus="Ggaba", status="approved")
        self.cand_ggaba1 = Candidate(election_id=self.election.id, position_id=self.pos_ggaba.id, full_name="Ggaba Cand 1", course="BCS", campus="Ggaba", status="approved")
        self.cand_fem1 = Candidate(election_id=self.election.id, position_id=self.pos_female.id, full_name="Female Cand 1", course="BED", campus="Luweero", status="approved")

        db.session.add_all([self.cand_pres1, self.cand_pres2, self.cand_ggaba1, self.cand_fem1])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    # --------------------------------------------------------------------------
    # 1. Ballot Secrecy Architecture Verification
    # --------------------------------------------------------------------------
    def test_ballot_secrecy_decoupling(self):
        """Verify that votes table contains NO voter identifier or join key to student."""
        vote_columns = [col.name for col in Vote.__table__.columns]
        self.assertNotIn('student_id', vote_columns, "Critical: student_id must NOT exist in votes table!")
        self.assertNotIn('voter_id', vote_columns, "Critical: voter_id must NOT exist in votes table!")
        self.assertNotIn('user_id', vote_columns, "Critical: user_id must NOT exist in votes table!")
        self.assertNotIn('receipt_token', vote_columns, "Critical: receipt_token must NOT exist in votes table!")

        part_columns = [col.name for col in VoterParticipation.__table__.columns]
        self.assertNotIn('candidate_id', part_columns, "Critical: candidate_id must NOT exist in voter_participation!")
        self.assertNotIn('position_id', part_columns, "Critical: position_id must NOT exist in voter_participation!")

    # --------------------------------------------------------------------------
    # 2. Dynamic Eligibility Filtering
    # --------------------------------------------------------------------------
    def test_eligibility_filtering(self):
        """Verify students only receive positions matching their campus, faculty, and gender."""
        # s1: Male, Ggaba Main Campus
        s1_eligible = ElectionService.get_eligible_positions_for_student(self.s1, self.election.id)
        s1_titles = [p.title for p in s1_eligible]

        self.assertIn("Guild President", s1_titles)
        self.assertIn("Ggaba Campus Representative", s1_titles)
        self.assertNotIn("Female Affairs Minister", s1_titles, "Male student must not be eligible for Female Affairs")

        # s2: Female, Luweero Campus
        s2_eligible = ElectionService.get_eligible_positions_for_student(self.s2, self.election.id)
        s2_titles = [p.title for p in s2_eligible]

        self.assertIn("Guild President", s2_titles)
        self.assertNotIn("Ggaba Campus Representative", s2_titles, "Luweero student must not see Ggaba Campus Rep")
        self.assertIn("Female Affairs Minister", s2_titles, "Female student must see Female Affairs")

    # --------------------------------------------------------------------------
    # 3. Double Voting Prevention & Atomic Casting
    # --------------------------------------------------------------------------
    def test_single_vote_and_double_vote_rejection(self):
        """Test ballot submission, participation receipt issuance, and strict double-vote rejection."""
        choices = {
            str(self.pos_president.id): self.cand_pres1.id,
            str(self.pos_ggaba.id): self.cand_ggaba1.id
        }

        # First vote should succeed
        success, receipt, msg = ElectionService.cast_ballot(self.s1, self.election, choices, "127.0.0.1")
        self.assertTrue(success)
        self.assertIsNotNone(receipt)
        self.assertTrue(receipt.startswith("KU-"))
        self.assertEqual(msg, "Your vote has been cast successfully.")

        # Verify voter participation record exists in Table A
        self.assertTrue(ElectionService.has_student_voted(self.s1.id, self.election.id))
        vp = VoterParticipation.query.filter_by(student_id=self.s1.id, election_id=self.election.id).first()
        self.assertEqual(vp.receipt_token, receipt)

        # Verify votes recorded in Table B
        pres_votes = Vote.query.filter_by(position_id=self.pos_president.id, candidate_id=self.cand_pres1.id).count()
        self.assertEqual(pres_votes, 1)

        # Attempting second vote with s1 MUST fail
        success2, receipt2, msg2 = ElectionService.cast_ballot(self.s1, self.election, choices, "127.0.0.1")
        self.assertFalse(success2)
        self.assertIsNone(receipt2)
        self.assertIn("Double voting detected", msg2)

    # --------------------------------------------------------------------------
    # 4. Election Timing Window Boundaries
    # --------------------------------------------------------------------------
    def test_election_closed_rejection(self):
        """Test that ballots are rejected when an election is closed."""
        closed_election = Election(
            title="Closed Election",
            academic_year="2025/2026",
            start_time=self.now - timedelta(days=2),
            end_time=self.now - timedelta(days=1),
            status="closed",
            created_by=self.admin.id
        )
        db.session.add(closed_election)
        db.session.commit()

        choices = {str(self.pos_president.id): self.cand_pres1.id}
        success, receipt, msg = ElectionService.cast_ballot(self.s1, closed_election, choices, "127.0.0.1")
        self.assertFalse(success)
        self.assertIn("closed", msg.lower())

    # --------------------------------------------------------------------------
    # 5. Electoral Commission Results Publishing Gate
    # --------------------------------------------------------------------------
    def test_ec_results_gate(self):
        """Test that results are hidden until approved and published by EC."""
        # Unapproved / Active election: allow_unapproved=False should return None
        results_public = ElectionService.get_election_results(self.election.id, allow_unapproved=False)
        self.assertIsNone(results_public, "Public results must be hidden prior to EC approval")

        # Admin preview can view real-time tabulations
        results_admin = ElectionService.get_election_results(self.election.id, allow_unapproved=True)
        self.assertIsNotNone(results_admin)
        self.assertEqual(results_admin['election']['title'], self.election.title)

        # Publish the election
        self.election.status = 'results_published'
        self.election.results_approved_by = self.admin.id
        self.election.results_approved_at = utc_now()
        db.session.commit()

        # Public can now access certified results
        results_after_pub = ElectionService.get_election_results(self.election.id, allow_unapproved=False)
        self.assertIsNotNone(results_after_pub)
        self.assertEqual(results_after_pub['election']['status'], 'results_published')

    # --------------------------------------------------------------------------
    # 6. Registrar Verification & Password Security
    # --------------------------------------------------------------------------
    def test_registrar_verification_and_auth(self):
        """Test that registration validates against university records and password hashes correctly."""
        # Valid student password check
        self.assertTrue(self.s1.check_password("Student@123"))
        self.assertFalse(self.s1.check_password("WrongPassword"))

        # Verify matching registrar record
        valid_rec = UniversityRecord.query.filter_by(student_id="KU/TEST/001", reg_no="24/KU/T01/UG").first()
        self.assertIsNotNone(valid_rec)

        # Non-matching registrar record fails
        invalid_rec = UniversityRecord.query.filter_by(student_id="KU/FAKE/999", reg_no="99/KU/FAKE").first()
        self.assertIsNone(invalid_rec)

if __name__ == '__main__':
    unittest.main()
