from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
import json
from events.models import Event, Participant, Feedback, Certificate, UserProfile


class StrictRoleArchitectureTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin User (Superuser or profile.role == 'ADMIN')
        self.admin_user = User.objects.create_superuser(username='admin_user', password='password123', email='admin@test.com')

        # Organizer A & B
        self.organizer_a = User.objects.create_user(username='organizer_a', password='password123', email='organizerA@test.com')
        self.org_a_profile = UserProfile.objects.create(user=self.organizer_a, role='EVENT_ORGANIZER')

        self.organizer_b = User.objects.create_user(username='organizer_b', password='password123', email='organizerB@test.com')
        self.org_b_profile = UserProfile.objects.create(user=self.organizer_b, role='EVENT_ORGANIZER')

        # Attendance Staff
        self.staff_user = User.objects.create_user(username='staff_user', password='password123', email='staff@test.com')
        self.staff_profile = UserProfile.objects.create(user=self.staff_user, role='ATTENDANCE_STAFF')

        # Student User
        self.student_user = User.objects.create_user(username='student_user', password='password123', email='student@test.com')
        self.student_profile = UserProfile.objects.create(user=self.student_user, role='STUDENT')

        # Event 1 (Created by Organizer A)
        self.event_1 = Event.objects.create(
            name='AI Conference 2026',
            description='Artificial Intelligence Conference',
            date=timezone.now().date(),
            venue='Main Hall',
            capacity=100,
            organizer=self.organizer_a,
            status='REGISTRATION_OPEN'
        )

        # Participant for Student User
        self.participant = Participant.objects.create(
            user=self.student_user,
            student_id='CS2026100',
            name='Student User',
            email='student@test.com',
            event=self.event_1
        )

    # --- 1. Login Redirection by Role ---
    def test_login_redirection_routing(self):
        """Test each role redirects to its explicit dashboard upon login."""
        # Student -> /student/dashboard/
        self.client.login(username='student_user', password='password123')
        r_stud = self.client.get(reverse('index'))
        self.assertRedirects(r_stud, reverse('student_dashboard'))
        self.client.logout()

        # Organizer -> /organizer/dashboard/
        self.client.login(username='organizer_a', password='password123')
        r_org = self.client.get(reverse('index'))
        self.assertRedirects(r_org, reverse('organizer_dashboard'))
        self.client.logout()

        # Staff -> /staff/dashboard/
        self.client.login(username='staff_user', password='password123')
        r_staff = self.client.get(reverse('index'))
        self.assertRedirects(r_staff, reverse('staff_dashboard'))
        self.client.logout()

        # Admin -> /admin/dashboard/
        self.client.login(username='admin_user', password='password123')
        r_admin = self.client.get(reverse('index'))
        self.assertRedirects(r_admin, reverse('system_admin_dashboard'))
        self.client.logout()

    # --- 2. Strict Role Isolation & Decorators ---
    def test_student_role_isolation(self):
        """Test STUDENT cannot access organizer, staff, or admin endpoints."""
        self.client.login(username='student_user', password='password123')

        # Student -> Organizer Dashboard = 403
        self.assertEqual(self.client.get(reverse('organizer_dashboard')).status_code, 403)
        # Student -> Staff Scanner = 403
        self.assertEqual(self.client.get(reverse('scan_attendance')).status_code, 403)
        # Student -> Admin Dashboard = 403
        self.assertEqual(self.client.get(reverse('system_admin_dashboard')).status_code, 403)

    def test_organizer_role_isolation(self):
        """Test EVENT_ORGANIZER cannot access staff scanner, student registration, or admin dashboard."""
        self.client.login(username='organizer_a', password='password123')

        # Organizer -> Student Dashboard = 403
        self.assertEqual(self.client.get(reverse('student_dashboard')).status_code, 403)
        # Organizer -> Staff Scanner = 403
        self.assertEqual(self.client.get(reverse('scan_attendance')).status_code, 403)
        # Organizer -> Admin Dashboard = 403
        self.assertEqual(self.client.get(reverse('system_admin_dashboard')).status_code, 403)

    def test_staff_role_isolation(self):
        """Test ATTENDANCE_STAFF cannot access student workflow, organizer dashboard, or admin dashboard."""
        self.client.login(username='staff_user', password='password123')

        # Staff -> Student Dashboard = 403
        self.assertEqual(self.client.get(reverse('student_dashboard')).status_code, 403)
        # Staff -> Organizer Dashboard = 403
        self.assertEqual(self.client.get(reverse('organizer_dashboard')).status_code, 403)
        # Staff -> Event Creation = 403
        self.assertEqual(self.client.get(reverse('create_event')).status_code, 403)
        # Staff -> Admin Dashboard = 403
        self.assertEqual(self.client.get(reverse('system_admin_dashboard')).status_code, 403)

    def test_admin_role_isolation(self):
        """Test ADMIN accesses dedicated admin views but is blocked from student registration workflow."""
        self.client.login(username='admin_user', password='password123')

        # Admin -> Admin Dashboard = 200
        self.assertEqual(self.client.get(reverse('system_admin_dashboard')).status_code, 200)
        # Admin -> User Management = 200
        self.assertEqual(self.client.get(reverse('admin_user_management')).status_code, 200)

        # Admin -> Student Dashboard = 403 (Admin is not a student)
        self.assertEqual(self.client.get(reverse('student_dashboard')).status_code, 403)

    # --- 3. Dedicated Admin Views & User Management ---
    def test_admin_user_role_assignment(self):
        """Test Admin can promote/demote user roles via admin_user_management."""
        self.client.login(username='admin_user', password='password123')

        target_user = User.objects.create_user(username='promoteme', password='password123')
        resp = self.client.post(reverse('admin_user_management'), {
            'user_id': target_user.id,
            'role': 'EVENT_ORGANIZER'
        })
        self.assertEqual(resp.status_code, 302)

        profile = UserProfile.objects.get(user=target_user)
        self.assertEqual(profile.role, 'EVENT_ORGANIZER')

    # --- 4. Object-Level Ownership Tests ---
    def test_organizer_cannot_edit_other_organizer_event(self):
        """Test Organizer A cannot edit Organizer B's event."""
        event_b = Event.objects.create(
            name='Organizer B Event',
            date=timezone.now().date(),
            venue='Hall B',
            organizer=self.organizer_b
        )
        self.client.login(username='organizer_a', password='password123')

        edit_url = reverse('edit_event', kwargs={'pk': event_b.pk})
        self.assertEqual(self.client.get(edit_url).status_code, 403)
