"""Comprehensive end-to-end test suite for the FindIt Flask application."""
import os
import re
import tempfile
import unittest
from datetime import date, timedelta

from sqlalchemy import inspect as sa_inspect

from app import create_app
from app.extensions import db
from app.models.admin import AuditLog, ModerationAction, UserReport
from app.models.auth import Role, User, UserProfile
from app.models.claims import Claim, ClaimAnswer, ClaimReview, VerificationQuestion
from app.models.classification import (
    Brand,
    Category,
    ItemCondition,
    ReportStatus,
    ReportType,
    Subcategory,
)
from app.models.communication import Conversation, Message, Notification
from app.models.location import Building, CampusZone, Location
from app.models.reporting import ItemReport, ReportLocation, ReportStatusHistory
from app.models.search import ItemMatch, SavedSearch
from app.models.security import (
    CustodyLog,
    IncidentReport,
    PatrolZone,
    SecurityStaff,
    Shift,
    StorageLocation,
)
from seed import seed_all

EXPECTED_TABLES = {
    # Auth (7)
    'users',
    'user_profiles',
    'roles',
    'permissions',
    'user_roles',
    'role_permissions',
    'user_contacts',
    # Classification (6)
    'categories',
    'subcategories',
    'brands',
    'item_conditions',
    'report_types',
    'report_statuses',
    # Location (5)
    'campus_zones',
    'buildings',
    'floors',
    'rooms',
    'locations',
    # Reporting (4)
    'item_reports',
    'report_locations',
    'item_images',
    'report_status_history',
    # Search (5)
    'tags',
    'report_tags',
    'saved_searches',
    'saved_search_filters',
    'item_matches',
    # Claims (7)
    'claims',
    'claim_evidence',
    'verification_questions',
    'claim_answers',
    'claim_reviews',
    'handover_appointments',
    'handover_records',
    # Security (6)
    'security_staff',
    'patrol_zones',
    'shifts',
    'storage_locations',
    'custody_logs',
    'incident_reports',
    # Communication (4)
    'conversations',
    'conversation_participants',
    'messages',
    'notifications',
    # Admin (4)
    'user_reports',
    'moderation_actions',
    'audit_logs',
    'verification_tokens',
}


class FindItBaseTestCase(unittest.TestCase):
    """Base test case providing an isolated seeded Flask app and test client."""

    @classmethod
    def setUpClass(cls):
        cls.upload_dir = tempfile.TemporaryDirectory()
        cls.app = create_app('testing')
        cls.app.config['UPLOAD_FOLDER'] = cls.upload_dir.name
        cls.app.config['WTF_CSRF_ENABLED'] = True

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.engine.dispose()
        cls.upload_dir.cleanup()

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        seed_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def _extract_csrf_token(self, html):
        """Extract CSRF token from form hidden input or base meta tag."""
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
        if match:
            return match.group(1)
        meta_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
        if meta_match:
            return meta_match.group(1)
        self.fail('CSRF token not found in HTML response.')

    def _get_csrf(self, path='/login'):
        """Fetch a page and extract its CSRF token."""
        resp = self.client.get(path)
        self.assertEqual(resp.status_code, 200)
        return self._extract_csrf_token(resp.get_data(as_text=True))

    def _login(self, email, password, remember_me=False):
        """Log in a user via POST /login with a valid CSRF token."""
        token = self._get_csrf('/login')
        payload = {
            'csrf_token': token,
            'email': email,
            'password': password,
        }
        if remember_me:
            payload['remember_me'] = 'y'
        return self.client.post('/login', data=payload, follow_redirects=False)

    def _logout(self):
        """Log out the currently authenticated user."""
        return self.client.get('/logout', follow_redirects=False)


class TestSchemaAndSeed(FindItBaseTestCase):
    """Verify all 48 SQLAlchemy tables, foreign keys, and idempotent seeding."""

    def test_48_tables_registered_and_created_with_fks(self):
        metadata_tables = set(db.metadata.tables.keys())
        self.assertEqual(len(metadata_tables), 48)
        self.assertEqual(metadata_tables, EXPECTED_TABLES)

        inspector = sa_inspect(db.engine)
        sqlite_tables = set(inspector.get_table_names())
        self.assertEqual(sqlite_tables, EXPECTED_TABLES)

        # Check meaningful foreign keys on core domain tables
        fk_tables = [
            'user_profiles',
            'user_roles',
            'role_permissions',
            'subcategories',
            'buildings',
            'locations',
            'item_reports',
            'report_locations',
            'claims',
            'claim_answers',
            'custody_logs',
            'incident_reports',
            'messages',
            'moderation_actions',
        ]
        for table_name in fk_tables:
            fks = inspector.get_foreign_keys(table_name)
            self.assertGreater(len(fks), 0, f'Expected foreign keys on {table_name}')

    def test_seed_is_idempotent(self):
        initial_users = User.query.count()
        initial_categories = Category.query.count()
        initial_reports = ItemReport.query.count()

        seed_all()

        self.assertEqual(User.query.count(), initial_users)
        self.assertEqual(Category.query.count(), initial_categories)
        self.assertEqual(ItemReport.query.count(), initial_reports)

    def test_seed_demo_credentials_match_readme(self):
        demo_creds = [
            ('admin@findit.edu', 'Admin@1234', 'admin'),
            ('security@findit.edu', 'Security@1234', 'security'),
            ('student1@findit.edu', 'Student@1234', 'user'),
            ('student2@findit.edu', 'Student@1234', 'user'),
        ]
        for email, password, role_name in demo_creds:
            user = User.query.filter_by(email=email).first()
            self.assertIsNotNone(user, f'Missing seeded user {email}')
            self.assertTrue(user.check_password(password), f'Invalid password for {email}')
            self.assertTrue(user.has_role(role_name), f'User {email} missing role {role_name}')


class TestPublicRoutes(FindItBaseTestCase):
    """Verify all public GET routes render cleanly with HTTP 200."""

    def test_all_public_get_routes(self):
        location = Location.query.first()
        building = Building.query.first()
        report = ItemReport.query.first()
        student = User.query.filter_by(email='student1@findit.edu').first()

        routes = [
            '/',
            '/about',
            '/login',
            '/register',
            '/items/',
            '/items/lost',
            '/items/found',
            f'/items/{report.id}',
            '/search/',
            '/locations/',
            '/locations/zones',
            '/locations/buildings',
            f'/locations/{location.id}',
            f'/locations/buildings/{building.id}',
            f'/profile/{student.id}',
        ]
        for path in routes:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, f'Expected 200 on GET {path}, got {resp.status_code}')
            body = resp.get_data(as_text=True)
            self.assertNotIn('Traceback', body)
            self.assertNotIn('Internal Server Error', body)


class TestAuthAndSessions(FindItBaseTestCase):
    """Verify registration validation, login/logout, remember-me, sessions, and profile."""

    def test_registration_success_and_validation_failures(self):
        # 1. Duplicate email rejected
        token = self._get_csrf('/register')
        resp = self.client.post(
            '/register',
            data={
                'csrf_token': token,
                'username': 'new_unique_user',
                'email': 'student1@findit.edu',
                'password': 'ValidPass123',
                'confirm_password': 'ValidPass123',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('An account with that email already exists.', resp.get_data(as_text=True))

        # 2. Short password rejected
        token = self._get_csrf('/register')
        resp = self.client.post(
            '/register',
            data={
                'csrf_token': token,
                'username': 'short_pw_user',
                'email': 'shortpw@findit.edu',
                'password': '123',
                'confirm_password': '123',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Password must be at least 8 characters long.', resp.get_data(as_text=True))

        # 3. Mismatched passwords rejected
        token = self._get_csrf('/register')
        resp = self.client.post(
            '/register',
            data={
                'csrf_token': token,
                'username': 'mismatch_user',
                'email': 'mismatch@findit.edu',
                'password': 'ValidPass123',
                'confirm_password': 'DifferentPass123',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Passwords must match.', resp.get_data(as_text=True))

        # 4. Valid registration succeeds with PRG + UserProfile + 'user' role
        token = self._get_csrf('/register')
        resp = self.client.post(
            '/register',
            data={
                'csrf_token': token,
                'username': 'jordan_lee',
                'email': 'jordan@findit.edu',
                'password': 'StrongPassword1',
                'confirm_password': 'StrongPassword1',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.location.endswith('/login'))

        follow = self.client.get(resp.location)
        self.assertEqual(follow.status_code, 200)
        self.assertIn('Registration successful! You can now log in.', follow.get_data(as_text=True))

        new_user = User.query.filter_by(email='jordan@findit.edu').first()
        self.assertIsNotNone(new_user)
        self.assertIsNotNone(new_user.profile)
        self.assertTrue(new_user.has_role('user'))

    def test_login_logout_remember_me_and_session_tracking(self):
        # Invalid login
        resp = self._login('student1@findit.edu', 'WrongPass999')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Invalid email or password.', resp.get_data(as_text=True))

        # Valid login with remember_me
        resp = self._login('student1@findit.edu', 'Student@1234', remember_me=True)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.location.endswith('/'))

        # Remember-me cookie should be set by Flask-Login
        set_cookies = resp.headers.getlist('Set-Cookie')
        self.assertTrue(
            any('remember_token=' in c for c in set_cookies),
            f'Expected remember_token cookie in {set_cookies}',
        )

        # Follow redirect and verify flash + session visit_count
        home = self.client.get(resp.location)
        self.assertEqual(home.status_code, 200)
        self.assertIn('Welcome back, alex_chen!', home.get_data(as_text=True))

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('username'), 'alex_chen')
            self.assertGreaterEqual(sess.get('visit_count', 0), 1)

        # Session tracking: recently_viewed and last_search
        report = ItemReport.query.first()
        self.client.get(f'/items/{report.id}')
        self.client.get('/search/?keyword=AirPods')
        with self.client.session_transaction() as sess:
            self.assertIn(report.id, sess.get('recently_viewed', []))
            self.assertEqual(sess.get('last_search', {}).get('keyword'), 'AirPods')

        # Logout
        logout_resp = self._logout()
        self.assertEqual(logout_resp.status_code, 302)
        after_logout = self.client.get(logout_resp.location)
        self.assertIn('You have been logged out.', after_logout.get_data(as_text=True))
        with self.client.session_transaction() as sess:
            self.assertNotIn('user_id', sess)

    def test_profile_view_and_edit_prg(self):
        self._login('student1@findit.edu', 'Student@1234')

        prof_resp = self.client.get('/profile')
        self.assertEqual(prof_resp.status_code, 200)
        self.assertIn('alex_chen', prof_resp.get_data(as_text=True))

        token = self._get_csrf('/profile/edit')
        edit_resp = self.client.post(
            '/profile/edit',
            data={
                'csrf_token': token,
                'first_name': 'Alex',
                'last_name': 'Chen-Updated',
                'department': 'Software Engineering',
                'reg_no': 'STU-999',
                'bio': 'Updated bio text for test verification.',
            },
            follow_redirects=False,
        )
        self.assertEqual(edit_resp.status_code, 302)
        self.assertTrue(edit_resp.location.endswith('/profile'))

        followed = self.client.get(edit_resp.location)
        self.assertEqual(followed.status_code, 200)
        body = followed.get_data(as_text=True)
        self.assertIn('Profile updated successfully.', body)
        self.assertIn('Chen-Updated', body)
        self.assertIn('Software Engineering', body)


class TestItemsCRUD(FindItBaseTestCase):
    """Verify full Items CRUD, validation, ownership authorization, PRG, and POST-only delete."""

    def test_create_read_update_delete_and_owner_checks(self):
        self._login('student1@findit.edu', 'Student@1234')

        category = Category.query.first()
        subcat = Subcategory.query.filter_by(category_id=category.id).first()
        brand = Brand.query.first()
        cond = ItemCondition.query.first()
        lost_type = ReportType.query.filter_by(type_name='lost').first()
        location = Location.query.first()

        # Server-side validation failure: short title + missing report_type_id
        token = self._get_csrf('/items/create')
        bad_resp = self.client.post(
            '/items/create',
            data={
                'csrf_token': token,
                'title': 'ab',
                'description': 'short',
                'report_type_id': '0',
            },
            follow_redirects=False,
        )
        self.assertEqual(bad_resp.status_code, 200)
        bad_html = bad_resp.get_data(as_text=True)
        self.assertIn('Title must be between 3 and 200 characters.', bad_html)
        self.assertIn('Description must be at least 10 characters.', bad_html)

        # Valid create (PRG)
        token = self._get_csrf('/items/create')
        create_resp = self.client.post(
            '/items/create',
            data={
                'csrf_token': token,
                'title': 'Lost Titanium Keyring',
                'description': 'Lost a titanium keyring with two brass keys and a gym fob near the library.',
                'category_id': str(category.id),
                'subcategory_id': str(subcat.id),
                'brand_id': str(brand.id),
                'condition_id': str(cond.id),
                'report_type_id': str(lost_type.id),
                'location_id': str(location.id),
                'specific_location': 'Second floor quiet desk',
                'event_date': (date.today() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'tags': 'keys, titanium, library',
            },
            follow_redirects=False,
        )
        self.assertEqual(create_resp.status_code, 302)
        report = ItemReport.query.filter_by(title='Lost Titanium Keyring').first()
        self.assertIsNotNone(report)
        self.assertTrue(create_resp.location.endswith(f'/items/{report.id}'))

        detail_resp = self.client.get(create_resp.location)
        self.assertEqual(detail_resp.status_code, 200)
        detail_html = detail_resp.get_data(as_text=True)
        self.assertIn('Item report created successfully!', detail_html)
        self.assertIn('Lost Titanium Keyring', detail_html)
        self.assertIn('#titanium', detail_html)

        # Non-owner check (student2 cannot edit or delete)
        self._logout()
        self._login('student2@findit.edu', 'Student@1234')

        self.assertEqual(self.client.get(f'/items/{report.id}/edit').status_code, 403)
        csrf_s2 = self._get_csrf(f'/items/{report.id}')
        self.assertEqual(
            self.client.post(
                f'/items/{report.id}/edit',
                data={
                    'csrf_token': csrf_s2,
                    'title': 'Hijacked Title',
                    'description': 'Attempted unauthorized modification of report.',
                    'report_type_id': str(lost_type.id),
                },
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(f'/items/{report.id}/delete', data={'csrf_token': csrf_s2}).status_code,
            403,
        )

        # Owner updates report and status
        self._logout()
        self._login('student1@findit.edu', 'Student@1234')
        returned_status = ReportStatus.query.filter_by(status_name='returned').first()
        edit_token = self._get_csrf(f'/items/{report.id}/edit')
        update_resp = self.client.post(
            f'/items/{report.id}/edit',
            data={
                'csrf_token': edit_token,
                'title': 'Lost Titanium Keyring Updated',
                'description': 'Updated description: found near desk and awaiting handover.',
                'category_id': str(category.id),
                'subcategory_id': str(subcat.id),
                'brand_id': str(brand.id),
                'condition_id': str(cond.id),
                'report_type_id': str(lost_type.id),
                'location_id': str(location.id),
                'specific_location': 'Front circulation desk',
                'event_date': (date.today() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'tags': 'keys, updated',
                'status_id': str(returned_status.id),
                'status_reason': 'Returned to owner',
            },
            follow_redirects=False,
        )
        self.assertEqual(update_resp.status_code, 302)
        updated_detail = self.client.get(update_resp.location)
        self.assertIn('Item report updated successfully.', updated_detail.get_data(as_text=True))
        self.assertIn('Lost Titanium Keyring Updated', updated_detail.get_data(as_text=True))

        # GET on delete endpoint must return 405 Method Not Allowed
        self.assertEqual(self.client.get(f'/items/{report.id}/delete').status_code, 405)

        # Owner deletes via POST
        del_token = self._extract_csrf_token(updated_detail.get_data(as_text=True))
        del_resp = self.client.post(
            f'/items/{report.id}/delete',
            data={'csrf_token': del_token},
            follow_redirects=False,
        )
        self.assertEqual(del_resp.status_code, 302)
        self.assertTrue(del_resp.location.endswith('/items/'))
        after_del = self.client.get(del_resp.location)
        self.assertIn('Item report deleted.', after_del.get_data(as_text=True))
        self.assertIsNone(db.session.get(ItemReport, report.id))


class TestClaimsAndVerification(FindItBaseTestCase):
    """Verify verification questions, claim submission, claim review, and my-claims."""

    def test_verification_questions_claim_submit_and_review_workflow(self):
        # Create a fresh found report owned by student2
        self._login('student2@findit.edu', 'Student@1234')
        found_type = ReportType.query.filter_by(type_name='found').first()
        token = self._get_csrf('/items/create')
        self.client.post(
            '/items/create',
            data={
                'csrf_token': token,
                'title': 'Found Silver Mechanical Pencil',
                'description': 'Found a Rotring silver mechanical pencil in Room 204 after lecture.',
                'report_type_id': str(found_type.id),
                'category_id': '0',
                'subcategory_id': '0',
                'brand_id': '0',
                'condition_id': '0',
                'location_id': '0',
            },
        )
        report = ItemReport.query.filter_by(title='Found Silver Mechanical Pencil').first()
        self.assertIsNotNone(report)

        # Owner adds a verification question
        q_token = self._get_csrf(f'/claims/questions/{report.id}')
        q_resp = self.client.post(
            f'/claims/questions/{report.id}',
            data={
                'csrf_token': q_token,
                'question': 'What lead size is engraved on the barrel?',
            },
            follow_redirects=False,
        )
        self.assertEqual(q_resp.status_code, 302)
        q_page = self.client.get(q_resp.location)
        self.assertIn('Verification question added.', q_page.get_data(as_text=True))

        question = VerificationQuestion.query.filter_by(report_id=report.id).first()
        self.assertIsNotNone(question)

        # Owner cannot claim own report
        own_claim_resp = self.client.get(f'/claims/submit/{report.id}', follow_redirects=False)
        self.assertEqual(own_claim_resp.status_code, 302)

        # Switch to student1 to submit claim
        self._logout()
        self._login('student1@findit.edu', 'Student@1234')

        # Missing verification answer should fail cleanly without 500
        c_token = self._get_csrf(f'/claims/submit/{report.id}')
        missing_ans = self.client.post(
            f'/claims/submit/{report.id}',
            data={
                'csrf_token': c_token,
                'claim_description': 'I lost my silver mechanical pencil right after the afternoon seminar.',
                'evidence_type': 'description',
                f'answer_{question.id}': '',
            },
            follow_redirects=False,
        )
        self.assertEqual(missing_ans.status_code, 200)
        self.assertIn('Please answer all verification questions', missing_ans.get_data(as_text=True))

        # Valid claim submission
        c_token = self._get_csrf(f'/claims/submit/{report.id}')
        claim_resp = self.client.post(
            f'/claims/submit/{report.id}',
            data={
                'csrf_token': c_token,
                'claim_description': 'I lost my silver Rotring mechanical pencil right after the afternoon seminar.',
                'evidence_type': 'description',
                'evidence_description': 'Has a small scratch near the clip.',
                f'answer_{question.id}': '0.5mm',
            },
            follow_redirects=False,
        )
        self.assertEqual(claim_resp.status_code, 302)
        claim = Claim.query.filter_by(report_id=report.id).first()
        self.assertIsNotNone(claim)
        self.assertEqual(claim.claim_status, 'pending')

        claim_detail = self.client.get(claim_resp.location)
        self.assertEqual(claim_detail.status_code, 200)
        self.assertIn('Your claim has been submitted for review.', claim_detail.get_data(as_text=True))
        self.assertIn('0.5mm', claim_detail.get_data(as_text=True))

        # My claims view
        my_claims_resp = self.client.get('/claims/my-claims')
        self.assertEqual(my_claims_resp.status_code, 200)
        self.assertIn('Found Silver Mechanical Pencil', my_claims_resp.get_data(as_text=True))

        # Owner (student2) reviews and approves claim
        self._logout()
        self._login('student2@findit.edu', 'Student@1234')
        rev_token = self._get_csrf(f'/claims/{claim.id}/review')
        rev_resp = self.client.post(
            f'/claims/{claim.id}/review',
            data={
                'csrf_token': rev_token,
                'decision': 'approved',
                'review_notes': 'Exact lead size and scratch confirmed.',
            },
            follow_redirects=False,
        )
        self.assertEqual(rev_resp.status_code, 302)
        rev_detail = self.client.get(rev_resp.location)
        self.assertEqual(rev_detail.status_code, 200)
        self.assertIn('Claim has been approved.', rev_detail.get_data(as_text=True))

        db.session.refresh(claim)
        db.session.refresh(report)
        self.assertEqual(claim.claim_status, 'approved')
        self.assertEqual(report.status.status_name.lower(), 'claimed')

    def test_reject_claim_workflow(self):
        # Security user rejects an existing pending claim from seed
        pending_claim = Claim.query.filter_by(claim_status='pending').first()
        self.assertIsNotNone(pending_claim)

        self._login('security@findit.edu', 'Security@1234')
        token = self._get_csrf(f'/claims/{pending_claim.id}/review')
        resp = self.client.post(
            f'/claims/{pending_claim.id}/review',
            data={
                'csrf_token': token,
                'decision': 'rejected',
                'review_notes': 'Unable to verify ownership details.',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        followed = self.client.get(resp.location)
        self.assertIn('Claim has been rejected.', followed.get_data(as_text=True))
        db.session.refresh(pending_claim)
        self.assertEqual(pending_claim.claim_status, 'rejected')


class TestSearchAndMatching(FindItBaseTestCase):
    """Verify filtered search, saved search create/delete, and matches page."""

    def test_search_filter_save_delete_and_matches(self):
        self._login('student1@findit.edu', 'Student@1234')

        electronics = Category.query.filter_by(category_name='Electronics').first()
        lost_type = ReportType.query.filter_by(type_name='lost').first()

        search_url = f'/search/?keyword=AirPods&category_id={electronics.id}&report_type_id={lost_type.id}'
        resp = self.client.get(search_url)
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('AirPods', html)

        # Save search via POST
        save_token = self._extract_csrf_token(html)
        save_resp = self.client.post(
            '/search/save',
            data={
                'csrf_token': save_token,
                'search_name': 'Lost AirPods Watch',
                'keyword': 'AirPods',
                'category_id': str(electronics.id),
                'report_type_id': str(lost_type.id),
            },
            follow_redirects=False,
        )
        self.assertEqual(save_resp.status_code, 302)
        self.assertTrue(save_resp.location.endswith('/search/saved'))

        saved_page = self.client.get(save_resp.location)
        self.assertEqual(saved_page.status_code, 200)
        saved_html = saved_page.get_data(as_text=True)
        self.assertIn('Search saved successfully.', saved_html)
        self.assertIn('Lost AirPods Watch', saved_html)

        saved_obj = SavedSearch.query.filter_by(search_name='Lost AirPods Watch').first()
        self.assertIsNotNone(saved_obj)

        # Non-owner cannot delete
        self._logout()
        self._login('student2@findit.edu', 'Student@1234')
        s2_token = self._get_csrf('/search/saved')
        self.assertEqual(
            self.client.post(
                f'/search/saved/{saved_obj.id}/delete',
                data={'csrf_token': s2_token},
            ).status_code,
            403,
        )

        # Owner deletes saved search
        self._logout()
        self._login('student1@findit.edu', 'Student@1234')
        del_token = self._get_csrf('/search/saved')
        del_resp = self.client.post(
            f'/search/saved/{saved_obj.id}/delete',
            data={'csrf_token': del_token},
            follow_redirects=False,
        )
        self.assertEqual(del_resp.status_code, 302)
        after_del = self.client.get(del_resp.location)
        self.assertIn('Saved search deleted.', after_del.get_data(as_text=True))
        self.assertIsNone(db.session.get(SavedSearch, saved_obj.id))

        # Matches page
        matches_resp = self.client.get('/search/matches')
        self.assertEqual(matches_resp.status_code, 200)
        self.assertGreater(ItemMatch.query.count(), 0)


class TestMessagingAndNotifications(FindItBaseTestCase):
    """Verify conversation start, messaging, notifications, and mark-as-read."""

    def test_start_conversation_send_message_and_notifications(self):
        student2 = User.query.filter_by(email='student2@findit.edu').first()
        # Pick a report owned by student2 that doesn't already have a conversation with student1, or create one
        self._login('student2@findit.edu', 'Student@1234')
        found_type = ReportType.query.filter_by(type_name='found').first()
        token = self._get_csrf('/items/create')
        self.client.post(
            '/items/create',
            data={
                'csrf_token': token,
                'title': 'Found Umbrella in Cafeteria',
                'description': 'Black compact umbrella found under table 4 in campus cafeteria.',
                'report_type_id': str(found_type.id),
                'category_id': '0',
                'subcategory_id': '0',
                'brand_id': '0',
                'condition_id': '0',
                'location_id': '0',
            },
        )
        report = ItemReport.query.filter_by(title='Found Umbrella in Cafeteria').first()
        self._logout()

        # Student1 starts conversation with student2
        self._login('student1@findit.edu', 'Student@1234')
        detail_html = self.client.get(f'/items/{report.id}').get_data(as_text=True)
        csrf_token = self._extract_csrf_token(detail_html)
        start_resp = self.client.post(
            f'/messaging/start/{report.id}',
            data={'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(start_resp.status_code, 302)
        conv = Conversation.query.filter_by(report_id=report.id).first()
        self.assertIsNotNone(conv)

        conv_page = self.client.get(start_resp.location)
        self.assertEqual(conv_page.status_code, 200)
        self.assertIn('Conversation started.', conv_page.get_data(as_text=True))

        # Student1 sends a message
        msg_token = self._extract_csrf_token(conv_page.get_data(as_text=True))
        msg_resp = self.client.post(
            f'/messaging/{conv.id}',
            data={
                'csrf_token': msg_token,
                'message_text': 'Hi! Does the umbrella have a wooden curved handle?',
            },
            follow_redirects=False,
        )
        self.assertEqual(msg_resp.status_code, 302)
        conv_after = self.client.get(msg_resp.location)
        self.assertIn('Message sent.', conv_after.get_data(as_text=True))
        self.assertIn('wooden curved handle', conv_after.get_data(as_text=True))

        # Inbox page
        inbox = self.client.get('/messaging/')
        self.assertEqual(inbox.status_code, 200)
        self.assertIn('Found Umbrella in Cafeteria', inbox.get_data(as_text=True))

        # Student2 checks notifications and marks unread notification read
        self._logout()
        self._login('student2@findit.edu', 'Student@1234')
        notif_resp = self.client.get('/messaging/notifications')
        self.assertEqual(notif_resp.status_code, 200)
        notif_html = notif_resp.get_data(as_text=True)
        self.assertIn('New Message', notif_html)

        unread_notif = Notification.query.filter_by(user_id=student2.id, is_read=False).first()
        self.assertIsNotNone(unread_notif)

        read_token = self._extract_csrf_token(notif_html)
        read_resp = self.client.post(
            f'/messaging/notifications/{unread_notif.id}/read',
            data={'csrf_token': read_token},
            follow_redirects=False,
        )
        self.assertEqual(read_resp.status_code, 302)
        notif_after = self.client.get(read_resp.location)
        self.assertIn('Notification marked as read.', notif_after.get_data(as_text=True))
        db.session.refresh(unread_notif)
        self.assertTrue(unread_notif.is_read)


class TestSecurityRoleRoutes(FindItBaseTestCase):
    """Verify security role access control and custody, incident, shift, storage workflows."""

    def test_access_control_blocks_non_security_and_allows_security_and_admin(self):
        # Unauthenticated redirects to login
        self.assertEqual(self.client.get('/security/dashboard').status_code, 302)

        # Standard user receives 403
        self._login('student1@findit.edu', 'Student@1234')
        for route in [
            '/security/dashboard',
            '/security/custody',
            '/security/custody/log',
            '/security/incidents',
            '/security/incidents/create',
            '/security/shifts',
            '/security/shifts/create',
            '/security/storage',
            '/security/storage/create',
        ]:
            self.assertEqual(self.client.get(route).status_code, 403, f'Expected 403 for student on {route}')

        # Admin is allowed
        self._logout()
        self._login('admin@findit.edu', 'Admin@1234')
        self.assertEqual(self.client.get('/security/dashboard').status_code, 200)

        # Security user is allowed
        self._logout()
        self._login('security@findit.edu', 'Security@1234')
        self.assertEqual(self.client.get('/security/dashboard').status_code, 200)

    def test_custody_incidents_shifts_and_storage_workflows(self):
        self._login('security@findit.edu', 'Security@1234')

        report = ItemReport.query.first()
        storage = StorageLocation.query.first()
        location = Location.query.first()
        building = Building.query.first()
        staff = SecurityStaff.query.first()
        patrol_zone = PatrolZone.query.first()

        # Custody list & log
        self.assertEqual(self.client.get('/security/custody').status_code, 200)
        token = self._get_csrf('/security/custody/log')
        custody_resp = self.client.post(
            '/security/custody/log',
            data={
                'csrf_token': token,
                'report_id': str(report.id),
                'storage_location_id': str(storage.id),
                'action': 'transferred',
            },
            follow_redirects=False,
        )
        self.assertEqual(custody_resp.status_code, 302)
        self.assertIn('Custody action logged successfully.', self.client.get(custody_resp.location).get_data(as_text=True))

        # Incidents list, create, detail
        self.assertEqual(self.client.get('/security/incidents').status_code, 200)
        token = self._get_csrf('/security/incidents/create')
        inc_resp = self.client.post(
            '/security/incidents/create',
            data={
                'csrf_token': token,
                'location_id': str(location.id),
                'report_id': str(report.id),
                'severity': 'medium',
                'description': 'Suspicious unclaimed bag checked and cleared at main desk.',
            },
            follow_redirects=False,
        )
        self.assertEqual(inc_resp.status_code, 302)
        self.assertIn('Incident report filed.', self.client.get(inc_resp.location).get_data(as_text=True))

        incident = IncidentReport.query.order_by(IncidentReport.id.desc()).first()
        inc_detail = self.client.get(f'/security/incidents/{incident.id}')
        self.assertEqual(inc_detail.status_code, 200)
        self.assertIn('Suspicious unclaimed bag checked', inc_detail.get_data(as_text=True))

        # Shifts list & create
        self.assertEqual(self.client.get('/security/shifts').status_code, 200)
        token = self._get_csrf('/security/shifts/create')
        shift_resp = self.client.post(
            '/security/shifts/create',
            data={
                'csrf_token': token,
                'staff_id': str(staff.id),
                'patrol_zone_id': str(patrol_zone.id),
                'shift_date': (date.today() + timedelta(days=2)).strftime('%Y-%m-%d'),
                'start_time': '09:00',
                'end_time': '17:00',
            },
            follow_redirects=False,
        )
        self.assertEqual(shift_resp.status_code, 302)
        self.assertIn('Security shift scheduled.', self.client.get(shift_resp.location).get_data(as_text=True))

        # Storage list & create
        self.assertEqual(self.client.get('/security/storage').status_code, 200)
        token = self._get_csrf('/security/storage/create')
        storage_resp = self.client.post(
            '/security/storage/create',
            data={
                'csrf_token': token,
                'name': 'North Locker Vault C',
                'building_id': str(building.id),
                'capacity': '75',
            },
            follow_redirects=False,
        )
        self.assertEqual(storage_resp.status_code, 302)
        after_storage = self.client.get(storage_resp.location)
        self.assertIn('Storage location created.', after_storage.get_data(as_text=True))
        self.assertIn('North Locker Vault C', after_storage.get_data(as_text=True))


class TestAdminRoleRoutes(FindItBaseTestCase):
    """Verify admin access control, user management, moderation, audit log, and taxonomy CRUD."""

    def test_access_control_blocks_non_admin(self):
        self.assertEqual(self.client.get('/admin/dashboard').status_code, 302)

        for email, pw in [
            ('student1@findit.edu', 'Student@1234'),
            ('security@findit.edu', 'Security@1234'),
        ]:
            self._login(email, pw)
            for route in [
                '/admin/dashboard',
                '/admin/users',
                '/admin/reports',
                '/admin/moderation',
                '/admin/audit-log',
                '/admin/categories',
                '/admin/brands',
                '/admin/locations',
            ]:
                self.assertEqual(self.client.get(route).status_code, 403, f'Expected 403 for {email} on {route}')
            self._logout()

    def test_admin_dashboard_users_reports_moderation_audit_and_taxonomy_crud(self):
        self._login('admin@findit.edu', 'Admin@1234')

        # Dashboard & Users
        self.assertEqual(self.client.get('/admin/dashboard').status_code, 200)
        self.assertEqual(self.client.get('/admin/users').status_code, 200)

        student2 = User.query.filter_by(email='student2@findit.edu').first()
        user_detail = self.client.get(f'/admin/users/{student2.id}')
        self.assertEqual(user_detail.status_code, 200)

        # Toggle user active/inactive
        csrf = self._extract_csrf_token(user_detail.get_data(as_text=True))
        toggle_resp = self.client.post(
            f'/admin/users/{student2.id}/toggle-active',
            data={'csrf_token': csrf},
            follow_redirects=False,
        )
        self.assertEqual(toggle_resp.status_code, 302)
        self.assertIn('is now inactive', self.client.get(toggle_resp.location).get_data(as_text=True))
        db.session.refresh(student2)
        self.assertFalse(student2.is_active)

        # Toggle back to active
        csrf = self._get_csrf(f'/admin/users/{student2.id}')
        toggle_back = self.client.post(
            f'/admin/users/{student2.id}/toggle-active',
            data={'csrf_token': csrf},
            follow_redirects=False,
        )
        self.assertEqual(toggle_back.status_code, 302)
        db.session.refresh(student2)
        self.assertTrue(student2.is_active)

        # User reports list & review
        self.assertEqual(self.client.get('/admin/reports').status_code, 200)
        user_report = UserReport.query.first()
        self.assertIsNotNone(user_report)
        rep_token = self._get_csrf(f'/admin/reports/{user_report.id}/review')
        rep_resp = self.client.post(
            f'/admin/reports/{user_report.id}/review',
            data={
                'csrf_token': rep_token,
                'status': 'reviewed',
                'action_type': 'warn',
                'reason': 'Issued polite reminder regarding duplicate reports.',
            },
            follow_redirects=False,
        )
        self.assertEqual(rep_resp.status_code, 302)
        self.assertIn('User report updated.', self.client.get(rep_resp.location).get_data(as_text=True))

        # Moderation & Audit Log
        mod_token = self._get_csrf('/admin/moderation')
        mod_resp = self.client.post(
            '/admin/moderation',
            data={
                'csrf_token': mod_token,
                'target_type': 'user',
                'target_id': str(student2.id),
                'action_type': 'warn',
                'reason': 'Routine test moderation warning recorded.',
            },
            follow_redirects=False,
        )
        self.assertEqual(mod_resp.status_code, 302)
        self.assertIn('Moderation action recorded.', self.client.get(mod_resp.location).get_data(as_text=True))
        self.assertEqual(self.client.get('/admin/audit-log').status_code, 200)

        # Categories CRUD (create -> edit -> delete)
        self.assertEqual(self.client.get('/admin/categories').status_code, 200)
        cat_token = self._get_csrf('/admin/categories/create')
        cat_create = self.client.post(
            '/admin/categories/create',
            data={
                'csrf_token': cat_token,
                'category_name': 'Musical Instruments',
                'description': 'Guitars, violins, and cases',
                'icon': 'bi-music-note-beamed',
            },
            follow_redirects=False,
        )
        self.assertEqual(cat_create.status_code, 302)
        self.assertIn('Category created successfully.', self.client.get(cat_create.location).get_data(as_text=True))

        cat = Category.query.filter_by(category_name='Musical Instruments').first()
        self.assertIsNotNone(cat)

        cat_edit_token = self._get_csrf(f'/admin/categories/{cat.id}/edit')
        cat_edit = self.client.post(
            f'/admin/categories/{cat.id}/edit',
            data={
                'csrf_token': cat_edit_token,
                'category_name': 'Musical Gear',
                'description': 'Updated instruments and audio gear',
                'icon': 'bi-music-note',
            },
            follow_redirects=False,
        )
        self.assertEqual(cat_edit.status_code, 302)
        cat_list_after = self.client.get(cat_edit.location)
        self.assertIn('Category updated successfully.', cat_list_after.get_data(as_text=True))
        self.assertIn('Musical Gear', cat_list_after.get_data(as_text=True))

        del_token = self._extract_csrf_token(cat_list_after.get_data(as_text=True))
        cat_del = self.client.post(
            f'/admin/categories/{cat.id}/delete',
            data={'csrf_token': del_token},
            follow_redirects=False,
        )
        self.assertEqual(cat_del.status_code, 302)
        self.assertIn('Category deleted.', self.client.get(cat_del.location).get_data(as_text=True))
        self.assertIsNone(db.session.get(Category, cat.id))

        # Brands list & create
        self.assertEqual(self.client.get('/admin/brands').status_code, 200)
        brand_token = self._get_csrf('/admin/brands/create')
        brand_resp = self.client.post(
            '/admin/brands/create',
            data={
                'csrf_token': brand_token,
                'brand_name': 'Logitech',
                'description': 'Keyboards, mice, and webcams',
            },
            follow_redirects=False,
        )
        self.assertEqual(brand_resp.status_code, 302)
        brand_after = self.client.get(brand_resp.location)
        self.assertIn('Brand created successfully.', brand_after.get_data(as_text=True))
        self.assertIn('Logitech', brand_after.get_data(as_text=True))

        # Locations list & create
        self.assertEqual(self.client.get('/admin/locations').status_code, 200)
        zone = CampusZone.query.first()
        loc_token = self._get_csrf('/admin/locations/create')
        loc_resp = self.client.post(
            '/admin/locations/create',
            data={
                'csrf_token': loc_token,
                'location_name': 'Innovation Hub Atrium',
                'zone_id': str(zone.id),
                'building_id': '0',
                'room_id': '0',
                'latitude': '37.4275',
                'longitude': '-122.1697',
            },
            follow_redirects=False,
        )
        self.assertEqual(loc_resp.status_code, 302)
        loc_after = self.client.get(loc_resp.location)
        self.assertIn('Location created successfully.', loc_after.get_data(as_text=True))
        self.assertIn('Innovation Hub Atrium', loc_after.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
