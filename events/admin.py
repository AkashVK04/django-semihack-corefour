from django.contrib import admin
from .models import Event, Participant, Feedback, Certificate, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'department', 'created_at']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email', 'department']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'venue', 'status', 'capacity', 'registered_count', 'attendance_rate']
    list_filter = ['status', 'date']
    search_fields = ['name', 'venue']


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'name', 'email', 'event', 'attendance', 'attendance_timestamp', 'feedback_submitted', 'eligible_for_certificate']
    list_filter = ['attendance', 'feedback_submitted', 'event']
    search_fields = ['student_id', 'name', 'email']
    readonly_fields = ['certificate_hash', 'registered_at']


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_id', 'participant', 'event', 'status', 'issued_at', 'revoked_at']
    list_filter = ['status', 'issued_at']
    search_fields = ['certificate_id', 'participant__name', 'participant__student_id', 'certificate_hash']
    readonly_fields = ['certificate_id', 'certificate_hash', 'issued_at', 'updated_at']


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['participant', 'rating', 'rating_content', 'rating_speaker', 'rating_organization', 'submitted_at']
    list_filter = ['rating']
