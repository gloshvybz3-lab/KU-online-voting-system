import unittest
from datetime import timedelta
from app import create_app
from config import TestingConfig
from models import db, Admin, Election, Position, Candidate, utc_now
from services.admin_service import AdminService, AdminServiceError


class AdminWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.chair = Admin(username='chair', email='chair@example.com', full_name='EC Chair', role='ec_chair')
        self.chair.set_password('secret')
        self.comm = Admin(username='comm', email='comm@example.com', full_name='Commissioner', role='ec_commissioner')
        self.comm.set_password('secret')
        db.session.add_all([self.chair, self.comm])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _election(self, title):
        now = utc_now()
        return AdminService.create_election(
            admin=self.chair, title=title, description='', academic_year='2026/2027',
            start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=4), status='draft'
        )

    def test_chair_can_create_election(self):
        election = self._election('Guild Elections')
        self.assertIsNotNone(election.id)
        self.assertEqual(election.created_by, self.chair.id)

    def test_position_and_candidate_are_scoped_to_same_election(self):
        election_a = self._election('Election A')
        election_b = self._election('Election B')
        position_a = AdminService.add_position(admin=self.chair, election_id=election_a.id,
                                                title='Guild President', description='', max_selections=1, priority_order=1)
        with self.assertRaises(AdminServiceError):
            AdminService.register_candidate(
                admin=self.comm, election_id=election_b.id, position_id=position_a.id,
                full_name='Cross Election Candidate', course='BIT', campus='Jinja', status='pending'
            )

    def test_duplicate_candidate_is_rejected(self):
        election = self._election('Election A')
        position = AdminService.add_position(admin=self.chair, election_id=election.id,
                                             title='President', description='', max_selections=1, priority_order=1)
        AdminService.register_candidate(admin=self.comm, election_id=election.id, position_id=position.id,
                                        full_name='Jane Doe', course='BIT', campus='Jinja', status='pending')
        with self.assertRaises(AdminServiceError):
            AdminService.register_candidate(admin=self.comm, election_id=election.id, position_id=position.id,
                                            full_name='jane doe', course='BIT', campus='Jinja', status='pending')

    def test_commissioner_cannot_create_election(self):
        with self.assertRaises(AdminServiceError):
            AdminService.create_election(admin=self.comm, title='Should Fail', description='', academic_year='2026/2027',
                                         start_time=utc_now() + timedelta(hours=1), end_time=utc_now() + timedelta(hours=4), status='draft')


if __name__ == '__main__':
    unittest.main()
