from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import hashlib


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('STUDENT', 'Student'),
        ('EVENT_ORGANIZER', 'Event Organizer'),
        ('ATTENDANCE_STAFF', 'Attendance Staff'),
        ('ADMIN', 'Administrator'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='STUDENT')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, default='Computer Science & Engineering')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_student(self):
        return self.role == 'STUDENT'

    @property
    def is_organizer(self):
        return self.role in ['EVENT_ORGANIZER', 'ADMIN'] or self.user.is_staff or self.user.is_superuser

    @property
    def is_attendance_staff(self):
        return self.role in ['ATTENDANCE_STAFF', 'EVENT_ORGANIZER', 'ADMIN'] or self.user.is_staff or self.user.is_superuser

    @property
    def is_admin(self):
        return self.role == 'ADMIN' or self.user.is_superuser


class Event(models.Model):
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('REGISTRATION_OPEN', 'Registration Open'),
        ('REGISTRATION_CLOSED', 'Registration Closed'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField()
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    venue = models.CharField(max_length=200, default='Main Auditorium')
    organizer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='organized_events')
    capacity = models.PositiveIntegerField(default=100)
    registration_deadline = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='REGISTRATION_OPEN')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def registered_count(self):
        return self.participants.count()

    @property
    def attendance_count(self):
        return self.participants.filter(attendance=True).count()

    @property
    def attendance_rate(self):
        total = self.registered_count
        if total == 0:
            return 0
        return round((self.attendance_count / total) * 100, 1)

    @property
    def is_registration_open(self):
        if self.status not in ['REGISTRATION_OPEN', 'UPCOMING']:
            return False
        if self.registration_deadline and timezone.now() > self.registration_deadline:
            return False
        if self.capacity > 0 and self.registered_count >= self.capacity:
            return False
        return True


class Participant(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='registrations')
    student_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    email = models.EmailField()
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='participants')
    registered_at = models.DateTimeField(auto_now_add=True)
    attendance = models.BooleanField(default=False)
    attendance_timestamp = models.DateTimeField(blank=True, null=True)
    attendance_marked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='marked_attendances')
    feedback_submitted = models.BooleanField(default=False)
    certificate_hash = models.CharField(max_length=64, unique=True, blank=True)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.certificate_hash:
            raw = f"{self.student_id}-{self.email}-{uuid.uuid4()}"
            self.certificate_hash = hashlib.sha256(raw.encode()).hexdigest()
        super().save(*args, **kwargs)

    @property
    def eligible_for_certificate(self):
        return self.attendance and self.feedback_submitted

    def __str__(self):
        return f"{self.name} ({self.student_id})"


class Certificate(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Eligibility'),
        ('ISSUED', 'Issued'),
        ('VALID', 'Valid'),
        ('REVOKED', 'Revoked'),
    ]

    certificate_id = models.CharField(max_length=50, unique=True)
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name='certificate_record')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='certificates')
    certificate_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='VALID')
    issued_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    revocation_reason = models.TextField(blank=True)
    revoked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='revoked_certificates')

    @classmethod
    def generate_certificate_id(cls):
        year = timezone.now().year
        count = cls.objects.count() + 1
        return f"EDU-{year}-{count:06d}"

    def __str__(self):
        return f"{self.certificate_id} — {self.participant.name} ({self.status})"


class Feedback(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name='feedback')
    rating = models.IntegerField(choices=RATING_CHOICES, default=5)
    rating_content = models.IntegerField(choices=RATING_CHOICES, default=5)
    rating_speaker = models.IntegerField(choices=RATING_CHOICES, default=5)
    rating_organization = models.IntegerField(choices=RATING_CHOICES, default=5)
    comments = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback by {self.participant.name} — {self.rating}★"
