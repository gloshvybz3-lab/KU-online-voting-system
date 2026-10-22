import unittest
import re
from datetime import timedelta
from app import create_app
from config import Config
from models import (
    db, UniversityRecord, Student, Admin, Election, Position,
    Candidate, EligibilityRule, VoterParticipation, Vote, utc_now
)

class CSRFTestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = True
    SECRET_KEY = "test-secret-key-csrf"
    SERVER_NAME = "localhost"

class TestCSRFAndIntegration(unittest.TestCase):
    def setUp(self):
        self.app = create_app(CSRFTestingConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.now = utc_now()
        # Seed test admin
        self.admin = Admin(
            username="ec_chair",
            email="chair@ku.ac.ug",
            full_name="EC Chair",
            role="ec_chair",
            is_active=True
        )
        self.admin.set_password("Chair@123")

        # Seed university record
        self.uni_rec = UniversityRecord(
            student_id="KU/2026/001",
            reg_no="26/KU/001/UG",
            full_name="Kato Paul",
            email="kato@ku.ac.ug",
            campus="Ggaba (Main Campus)",
            faculty="Faculty of Computer Science and Information Technology",
            course="Bachelor of Information Technology",
            year_of_study=2,
            gender="Male",
            is_registered_student=True
        )

        db.session.add_all([self.admin, self.uni_rec])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _extract_csrf_token(self, html_text):
        """Extracts csrf_token from hidden input field."""
        match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html_text)
        if match:
            return match.group(1)
        match = re.search(r'value=["\']([^"\']+)["\']\s+name=["\']csrf_token["\']', html_text)
        if match:
            return match.group(1)
        return None

    def test_login_page_renders_csrf_as_hidden_input_not_raw_text(self):
        """Verifies that the login page contains hidden csrf_token and does not dump raw token outside an input."""
        res = self.client.get('/auth/login')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        token = self._extract_csrf_token(html)
        self.assertIsNotNone(token, "CSRF token hidden input must exist on login form")
        self.assertTrue(len(token) > 10, "CSRF token must be non-empty")

        # Ensure the token does NOT appear outside an attribute / outside an input tag
        # Strip all input tags and check that token does not appear in body text
        html_without_inputs = re.sub(r'<input[^>]*>', '', html)
        html_without_meta = re.sub(r'<meta[^>]*>', '', html_without_inputs)
        self.assertNotIn(token, html_without_meta, "CSRF token must NOT appear as raw visible text in HTML")

    def test_csrf_protection_rejects_missing_token(self):
        """Verifies that submitting login form without CSRF token is rejected with 400 Bad Request."""
        res = self.client.post('/auth/login', data={
            'identifier': 'KU/2026/001',
            'password': 'any'
        })
        self.assertEqual(res.status_code, 400)

    def test_student_registration_url_redirects_to_login(self):
        """The legacy student registration endpoint no longer offers self-registration."""
        response = self.client.get('/auth/register')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/auth/login')
        self.assertIsNone(Student.query.filter_by(student_id=self.uni_rec.student_id).first())

    def test_admin_registers_students_and_sets_their_login_password(self):
        """Admins create student accounts and assign the login password."""
        with self.client.session_transaction() as session:
            session['_user_id'] = f'admin_{self.admin.id}'
            session['_fresh'] = True
        registry_page = self.client.get('/admin/students')
        admin_csrf = self._extract_csrf_token(registry_page.get_data(as_text=True))
        self.assertIsNotNone(admin_csrf)

        res_reg = self.client.post('/admin/students/register', data={
            'csrf_token': admin_csrf,
            'student_id': self.uni_rec.student_id,
            'reg_no': self.uni_rec.reg_no,
            'full_name': 'Incorrect Submitted Name',
            'email': 'incorrect@ku.ac.ug',
            'password': 'AdminSet@123',
            'campus': 'Mutundwe Campus',
            'faculty': 'Faculty of Education',
            'course': 'Incorrect Course',
            'year_of_study': '1',
            'gender': 'Female',
            'is_verified': 'true',
        })
        self.assertEqual(res_reg.status_code, 302)
        registered = Student.query.filter_by(student_id=self.uni_rec.student_id).one()
        self.assertTrue(registered.check_password('AdminSet@123'))
        self.assertFalse(registered.check_password('Password@123'))
        self.assertEqual(registered.full_name, self.uni_rec.full_name)
        self.assertEqual(registered.email, self.uni_rec.email)
        self.assertEqual(registered.campus, self.uni_rec.campus)
        self.assertEqual(registered.faculty, self.uni_rec.faculty)
        self.assertEqual(registered.course, self.uni_rec.course)
        self.assertEqual(registered.year_of_study, self.uni_rec.year_of_study)
        self.assertEqual(registered.gender, self.uni_rec.gender)
        self.assertTrue(registered.is_verified)

        election = Election(
            title='Eligibility Integration Election',
            academic_year='2026/2027',
            start_time=self.now - timedelta(hours=1),
            end_time=self.now + timedelta(hours=5),
            status='active',
        )
        db.session.add(election)
        db.session.flush()
        ggaba_position = Position(election_id=election.id, title='Ggaba Representative', priority_order=1)
        luweero_position = Position(election_id=election.id, title='Luweero Representative', priority_order=2)
        db.session.add_all([ggaba_position, luweero_position])
        db.session.flush()
        db.session.add_all([
            EligibilityRule(
                election_id=election.id, position_id=ggaba_position.id, campus='Ggaba Campus',
                faculty='ALL', course='ALL', year_of_study=0, gender='ALL'
            ),
            EligibilityRule(
                election_id=election.id, position_id=luweero_position.id, campus='Luweero Campus',
                faculty='ALL', course='ALL', year_of_study=0, gender='ALL'
            ),
        ])
        db.session.add_all([
            Candidate(
                election_id=election.id, position_id=ggaba_position.id,
                full_name='Ggaba Candidate', course='BIT', campus='Ggaba Campus', status='approved'
            ),
            Candidate(
                election_id=election.id, position_id=luweero_position.id,
                full_name='Luweero Candidate', course='BIT', campus='Luweero Campus', status='approved'
            ),
        ])
        db.session.commit()

        registered_student_id = registered.student_id
        election_id = election.id
        self.ctx.pop()
        try:
            self.client.get('/auth/logout')
            login_page = self.client.get('/auth/login')
            self.assertEqual(login_page.status_code, 200)
            login_csrf = self._extract_csrf_token(login_page.get_data(as_text=True))
            self.assertIsNotNone(login_csrf)
            student_login = self.client.post('/auth/login', data={
                'csrf_token': login_csrf,
                'identifier': registered_student_id,
                'password': 'AdminSet@123',
            }, headers={'Host': 'localhost'})
            self.assertEqual(student_login.status_code, 302)
            ballot_response = self.client.get(f'/voting/elections/{election_id}/ballot')
            ballot_html = ballot_response.get_data(as_text=True)
            self.assertEqual(ballot_response.status_code, 200)
            self.assertIn('Ggaba Representative', ballot_html)
            self.assertNotIn('Luweero Representative', ballot_html)
        finally:
            self.ctx = self.app.app_context()
            self.ctx.push()

    def test_voter_registry_campus_and_status_filters(self):
        """Registry filters use actual stored campus names and support all account states."""
        inactive = Student(
            student_id='KU/2026/101', reg_no='26/KU/101/UG', full_name='Inactive Ggaba',
            email='inactive@ku.ac.ug', campus='Ggaba Campus', faculty='Faculty of Education',
            course='Education', year_of_study=1, gender='Female', is_verified=True, is_active=False
        )
        inactive.set_password('Student@123')
        unverified = Student(
            student_id='KU/2026/102', reg_no='26/KU/102/UG', full_name='Unverified Jinja',
            email='unverified@ku.ac.ug', campus='Jinja Campus', faculty='Faculty of Education',
            course='Education', year_of_study=1, gender='Male', is_verified=False, is_active=True
        )
        unverified.set_password('Student@123')
        db.session.add_all([inactive, unverified])
        db.session.commit()

        with self.client.session_transaction() as session:
            session['_user_id'] = f'admin_{self.admin.id}'
            session['_fresh'] = True

        campus_response = self.client.get('/admin/students?campus=ggaba+campus')
        campus_html = campus_response.get_data(as_text=True)
        self.assertIn('Inactive Ggaba', campus_html)
        self.assertNotIn('Unverified Jinja', campus_html)
        self.assertIn('<option value="Ggaba Campus" selected>', campus_html)

        verified_response = self.client.get('/admin/students?status=verified')
        verified_html = verified_response.get_data(as_text=True)
        self.assertIn('Inactive Ggaba', verified_html)
        self.assertNotIn('Unverified Jinja', verified_html)

        unverified_response = self.client.get('/admin/students?status=unverified')
        unverified_html = unverified_response.get_data(as_text=True)
        self.assertNotIn('Inactive Ggaba', unverified_html)
        self.assertIn('Unverified Jinja', unverified_html)

        all_response = self.client.get('/admin/students')
        all_html = all_response.get_data(as_text=True)
        self.assertIn('Inactive Ggaba', all_html)
        self.assertIn('Unverified Jinja', all_html)
        self.assertNotIn('<option value="active"', all_html)
        self.assertNotIn('<option value="inactive"', all_html)

    def test_receipt_verification_via_get_and_post(self):
        """Verifies receipt validator handles both GET and POST with valid/invalid tokens."""
        # Seed voter participation
        el = Election(
            title="Guild Elections 2026",
            academic_year="2026/2027",
            start_time=self.now - timedelta(hours=1),
            end_time=self.now + timedelta(hours=5),
            status="active"
        )
        student = Student(
            student_id="KU/2026/001",
            reg_no="26/KU/001/UG",
            full_name="Kato Paul",
            email="kato@ku.ac.ug",
            campus="Ggaba (Main Campus)",
            faculty="Faculty of Computer Science and Information Technology",
            course="Bachelor of Information Technology",
            year_of_study=2,
            gender="Male"
        )
        student.set_password("Pass123")
        db.session.add_all([el, student])
        db.session.commit()

        vp = VoterParticipation(
            election_id=el.id,
            student_id=student.id,
            receipt_token="KU-TESTTOKEN12345",
            voted_at=self.now
        )
        db.session.add(vp)
        db.session.commit()

        # Test GET with token param (clicking link from confirmation screen)
        res_get = self.client.get('/verify-receipt?token=KU-TESTTOKEN12345')
        self.assertEqual(res_get.status_code, 200)
        self.assertIn('RECEIPT VERIFIED SUCCESSFULLY', res_get.get_data(as_text=True))
        self.assertIn('KU-TESTTOKEN12345', res_get.get_data(as_text=True))

        # Test POST with CSRF
        verify_page = self.client.get('/verify-receipt')
        csrf_token = self._extract_csrf_token(verify_page.get_data(as_text=True))
        res_post = self.client.post('/verify-receipt', data={
            'csrf_token': csrf_token,
            'token': 'KU-TESTTOKEN12345'
        })
        self.assertEqual(res_post.status_code, 200)
        self.assertIn('RECEIPT VERIFIED SUCCESSFULLY', res_post.get_data(as_text=True))

        # Test invalid token
        res_invalid = self.client.get('/verify-receipt?token=KU-DOESNOTEXIST')
        self.assertEqual(res_invalid.status_code, 200)
        self.assertIn('No recorded vote matches this receipt token', res_invalid.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
