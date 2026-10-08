import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'event_lifecycle.settings')
django.setup()

from django.contrib.auth.models import User
from events.models import UserProfile, Event, Participant
from django.utils import timezone

def create_seed_data():
    accounts = [
        ('student', 'student@test.com', 'STUDENT', False),
        ('organizerA', 'organizerA@test.com', 'EVENT_ORGANIZER', False),
        ('organizerB', 'organizerB@test.com', 'EVENT_ORGANIZER', False),
        ('staff', 'staff@test.com', 'ATTENDANCE_STAFF', False),
        ('admin', 'admin@test.com', 'ADMIN', True),
    ]

    for username, email, role, is_super in accounts:
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        user.set_password('password123')
        user.email = email
        user.is_superuser = is_super
        user.is_staff = is_super
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()
        print(f"[OK] Account ready: {username} ({role}) | password: password123")

    # Create sample events if missing
    org_a = User.objects.get(username='organizerA')
    org_b = User.objects.get(username='organizerB')

    e1, _ = Event.objects.get_or_create(
        name='AI & Innovation Summit 2026',
        defaults={
            'description': 'National Academic AI & Robotics Summit',
            'date': timezone.now().date(),
            'venue': 'Main Auditorium',
            'organizer': org_a,
            'capacity': 100,
            'status': 'REGISTRATION_OPEN'
        }
    )

    e2, _ = Event.objects.get_or_create(
        name='CyberSecurity Workshop 2026',
        defaults={
            'description': 'Ethical Hacking & Network Defense',
            'date': timezone.now().date(),
            'venue': 'Lab 3',
            'organizer': org_b,
            'capacity': 50,
            'status': 'REGISTRATION_OPEN'
        }
    )
    print("[OK] Sample Events initialized.")

if __name__ == '__main__':
    create_seed_data()
