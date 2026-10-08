import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Event, Participant, Feedback, Certificate, UserProfile
from .forms import RegistrationForm, FeedbackForm, EventForm, UserRegistrationForm, RevocationForm
from .utils import generate_qr_code, generate_certificate_pdf
from .decorators import student_required, organizer_required, staff_required, admin_required, get_user_role


def get_role_dashboard_name(user):
    """Helper to return exact dashboard view name for a user role."""
    if not user or not user.is_authenticated:
        return 'index'
    user_role = get_user_role(user)
    role_map = {
        'ADMIN': 'system_admin_dashboard',
        'EVENT_ORGANIZER': 'organizer_dashboard',
        'ATTENDANCE_STAFF': 'staff_dashboard',
        'STUDENT': 'student_dashboard',
    }
    return role_map.get(user_role, 'student_dashboard')


def index(request):
    """Home page. If user is authenticated, redirect to their role's specific dashboard."""
    if request.user.is_authenticated:
        return redirect(get_role_dashboard_name(request.user))
    events = Event.objects.annotate(count=Count('participants')).order_by('-date')
    return render(request, 'events/index.html', {'events': events})


@student_required
def register(request):
    """Event registration view strictly for STUDENT users."""
    event_id = request.GET.get('event')
    initial_data = {}
    if event_id:
        initial_data['event'] = event_id

    if not initial_data.get('email'):
        initial_data['email'] = request.user.email
        initial_data['name'] = request.user.get_full_name() or request.user.username

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            participant = form.save(commit=False)
            participant.user = request.user

            event = participant.event
            if not event.is_registration_open:
                messages.error(request, "⚠ Registration for this event is currently closed or full.")
                return redirect('student_dashboard')

            participant.save()

            try:
                domain = request.build_absolute_uri('/')[:-1]
                generate_qr_code(participant, domain=domain)
                participant.save()
            except Exception:
                pass

            messages.success(
                request,
                f"🎉 Registration successful! Welcome, {participant.name}. "
                f"Your Student ID is {participant.student_id}."
            )
            return redirect('registration_success', pk=participant.pk)
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        form = RegistrationForm(initial=initial_data)

    return render(request, 'events/register.html', {'form': form})


@student_required
def registration_success(request, pk):
    """Post-registration confirmation page showing participant QR code."""
    participant = get_object_or_404(Participant.objects.select_related('event'), pk=pk)
    if participant.user != request.user:
        raise PermissionDenied("You do not have permission to view this registration receipt.")
    return render(request, 'events/registration_success.html', {'participant': participant})


def verify_certificate(request, hash):
    """Public verification endpoint for scanned QR codes or hash links."""
    participant = Participant.objects.filter(certificate_hash=hash).select_related('event').first()
    if not participant:
        cert = Certificate.objects.filter(Q(certificate_hash=hash) | Q(certificate_id=hash)).select_related('participant', 'event').first()
        if cert:
            participant = cert.participant

    if not participant:
        return render(request, 'events/verify_certificate.html', {'status': 'NOT_FOUND', 'hash': hash}, status=404)

    certificate = Certificate.objects.filter(participant=participant).first()
    if participant.eligible_for_certificate and not certificate:
        certificate = Certificate.objects.create(
            participant=participant,
            event=participant.event,
            certificate_hash=participant.certificate_hash,
            certificate_id=Certificate.generate_certificate_id(),
            status='VALID'
        )

    return render(request, 'events/verify_certificate.html', {
        'participant': participant,
        'certificate': certificate,
        'event': participant.event,
        'status': certificate.status if certificate else ('PENDING' if not participant.eligible_for_certificate else 'VALID'),
    })


@organizer_required
def revoke_certificate(request, pk):
    """Endpoint strictly for EVENT_ORGANIZER users to revoke a certificate for their own events."""
    participant = get_object_or_404(Participant.objects.select_related('event'), pk=pk)

    if participant.event.organizer != request.user:
        raise PermissionDenied("You can only manage certificates for events you organize.")

    certificate, created = Certificate.objects.get_or_create(
        participant=participant,
        defaults={
            'event': participant.event,
            'certificate_hash': participant.certificate_hash,
            'certificate_id': Certificate.generate_certificate_id(),
            'status': 'VALID'
        }
    )

    if request.method == 'POST':
        form = RevocationForm(request.POST)
        if form.is_valid():
            certificate.status = 'REVOKED'
            certificate.revoked_at = timezone.now()
            certificate.revocation_reason = form.cleaned_data['reason']
            certificate.revoked_by = request.user
            certificate.save()
            messages.success(request, f"Certificate {certificate.certificate_id} has been REVOKED.")
            return redirect('organizer_dashboard')
    else:
        form = RevocationForm()

    return render(request, 'events/revoke_certificate.html', {
        'participant': participant,
        'certificate': certificate,
        'form': form
    })


@organizer_required
def restore_certificate(request, pk):
    """Endpoint strictly for EVENT_ORGANIZER users to reinstate a certificate for their own events."""
    participant = get_object_or_404(Participant.objects.select_related('event'), pk=pk)

    if participant.event.organizer != request.user:
        raise PermissionDenied("You can only manage certificates for events you organize.")

    certificate = get_object_or_404(Certificate, participant=participant)

    if request.method == 'POST':
        certificate.status = 'VALID'
        certificate.revoked_at = None
        certificate.revocation_reason = ''
        certificate.save()
        messages.success(request, f"Certificate {certificate.certificate_id} has been REINSTATED as VALID.")
        return redirect('organizer_dashboard')

    return render(request, 'events/restore_certificate.html', {
        'participant': participant,
        'certificate': certificate
    })


@staff_required
def staff_dashboard(request):
    """Dedicated dashboard for ATTENDANCE_STAFF users."""
    recent_scans = Participant.objects.filter(attendance=True, attendance_marked_by=request.user).select_related('event').order_by('-attendance_timestamp')[:15]
    return render(request, 'events/attendance_staff_dashboard.html', {'recent_scans': recent_scans})


@staff_required
def scan_attendance(request):
    """Staff interface with live camera QR scanner to mark attendance."""
    events = Event.objects.all()
    return render(request, 'events/scan_attendance.html', {'events': events})


@require_POST
@staff_required
def mark_qr_attendance(request):
    """AJAX POST endpoint for marking attendance via scanned QR code or hash."""
    try:
        data = json.loads(request.body)
        raw_qr = data.get('qr_data', '').strip()

        if not raw_qr:
            return JsonResponse({'status': 'error', 'message': 'Empty QR payload.'}, status=400)

        hash_val = raw_qr.rstrip('/').split('/')[-1]

        participant = Participant.objects.select_related('event').filter(
            Q(certificate_hash=hash_val) | Q(student_id__iexact=raw_qr)
        ).first()

        if not participant:
            return JsonResponse({'status': 'error', 'message': 'Participant QR code not found.'}, status=404)

        if participant.attendance:
            return JsonResponse({
                'status': 'already_marked',
                'message': f'Attendance already marked for {participant.name} ({participant.student_id}).',
                'participant': {
                    'name': participant.name,
                    'student_id': participant.student_id,
                    'event': participant.event.name,
                    'timestamp': participant.attendance_timestamp.strftime('%H:%M:%S') if participant.attendance_timestamp else ''
                }
            })

        participant.attendance = True
        participant.attendance_timestamp = timezone.now()
        participant.attendance_marked_by = request.user
        participant.save()

        return JsonResponse({
            'status': 'success',
            'message': f'✓ Attendance recorded for {participant.name} ({participant.student_id}).',
            'participant': {
                'name': participant.name,
                'student_id': participant.student_id,
                'event': participant.event.name,
                'timestamp': participant.attendance_timestamp.strftime('%H:%M:%S')
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@student_required
def student_dashboard(request):
    """Student portal strictly for STUDENT users."""
    registrations = Participant.objects.filter(user=request.user).select_related('event', 'certificate_record')
    available_events = Event.objects.filter(status='REGISTRATION_OPEN').order_by('-date')
    return render(request, 'events/student_dashboard.html', {
        'registrations': registrations,
        'available_events': available_events
    })


@organizer_required
def organizer_dashboard(request):
    """Organizer Portal strictly for EVENT_ORGANIZER users, scoped to own events."""
    base_participants = Participant.objects.filter(event__organizer=request.user).select_related('event', 'certificate_record', 'user')
    base_events = Event.objects.filter(organizer=request.user)

    participants = base_participants.order_by('-registered_at')

    # Filtering
    event_id = request.GET.get('event')
    search = request.GET.get('search', '').strip()
    attendance_filter = request.GET.get('attendance')

    if event_id:
        participants = participants.filter(event_id=event_id)
    if search:
        participants = participants.filter(
            Q(name__icontains=search) | Q(student_id__icontains=search) | Q(email__icontains=search)
        )
    if attendance_filter == '1':
        participants = participants.filter(attendance=True)
    elif attendance_filter == '0':
        participants = participants.filter(attendance=False)

    total_participants = base_participants.count()
    total_present = base_participants.filter(attendance=True).count()
    attendance_rate = round((total_present / total_participants * 100), 1) if total_participants > 0 else 0

    stats = {
        'total_events': base_events.count(),
        'total_participants': total_participants,
        'present': total_present,
        'attendance_rate': attendance_rate,
        'feedback_count': base_participants.filter(feedback_submitted=True).count(),
        'eligible_count': base_participants.filter(attendance=True, feedback_submitted=True).count(),
        'valid_certs': Certificate.objects.filter(event__in=base_events, status='VALID').count(),
        'revoked_certs': Certificate.objects.filter(event__in=base_events, status='REVOKED').count(),
        'avg_rating': round(Feedback.objects.filter(participant__in=base_participants).aggregate(avg=Avg('rating'))['avg'] or 5.0, 1),
    }

    return render(request, 'events/organizer_dashboard.html', {
        'participants': participants,
        'events': base_events,
        'stats': stats,
        'selected_event': event_id,
        'search': search,
    })


@organizer_required
def create_event(request):
    """Create a new academic event strictly for EVENT_ORGANIZER users."""
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, f"Event '{event.name}' successfully created!")
            return redirect('organizer_dashboard')
    else:
        form = EventForm()

    return render(request, 'events/event_form.html', {'form': form, 'action': 'Create'})


@organizer_required
def edit_event(request, pk):
    """Edit existing event parameters strictly for EVENT_ORGANIZER users."""
    event = get_object_or_404(Event, pk=pk)

    if event.organizer != request.user:
        raise PermissionDenied("You can only edit events you organize.")

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f"Event '{event.name}' successfully updated!")
            return redirect('organizer_dashboard')
    else:
        form = EventForm(instance=event)

    return render(request, 'events/event_form.html', {'form': form, 'action': 'Edit', 'event': event})


@student_required
def feedback(request, pk):
    """Multi-metric event feedback view strictly for STUDENT users."""
    participant = get_object_or_404(Participant.objects.select_related('event'), pk=pk)

    if participant.user != request.user:
        raise PermissionDenied("You can only submit feedback for your own event registration.")

    if hasattr(participant, 'feedback'):
        messages.info(request, "Feedback has already been submitted for this registration.")
        return redirect('student_dashboard')

    if not participant.attendance:
        messages.warning(request, "⚠ Feedback submission requires confirmed event attendance.")
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.participant = participant
            fb.save()
            participant.feedback_submitted = True
            participant.save()

            Certificate.objects.get_or_create(
                participant=participant,
                defaults={
                    'event': participant.event,
                    'certificate_hash': participant.certificate_hash,
                    'certificate_id': Certificate.generate_certificate_id(),
                    'status': 'VALID'
                }
            )

            messages.success(request, "🎉 Thank you for your feedback! Your official digital certificate is ready.")
            return redirect('verify_certificate', hash=participant.certificate_hash)
    else:
        form = FeedbackForm()

    return render(request, 'events/feedback.html', {'form': form, 'participant': participant})


@login_required
def certificate(request, hash):
    """Gatekeeper PDF certificate download endpoint."""
    participant = get_object_or_404(Participant.objects.select_related('event'), certificate_hash=hash)

    # Verification: Must be the participant or an admin/organizer
    user_role = get_user_role(request.user)
    is_management = user_role in ['ADMIN', 'EVENT_ORGANIZER']
    if participant.user and participant.user != request.user and not is_management:
        raise PermissionDenied("You do not have permission to download this certificate.")

    if not participant.eligible_for_certificate:
        missing = []
        if not participant.attendance:
            missing.append("Event attendance must be marked by staff")
        if not participant.feedback_submitted:
            missing.append("Event feedback form must be submitted")
        return render(request, 'events/certificate_denied.html', {
            'participant': participant,
            'missing': missing,
        }, status=403)

    certificate_obj, created = Certificate.objects.get_or_create(
        participant=participant,
        defaults={
            'event': participant.event,
            'certificate_hash': participant.certificate_hash,
            'certificate_id': Certificate.generate_certificate_id(),
            'status': 'VALID'
        }
    )

    if certificate_obj.status == 'REVOKED':
        messages.error(request, "🚫 This certificate has been REVOKED and cannot be downloaded.")
        return redirect('verify_certificate', hash=hash)

    buffer = generate_certificate_pdf(participant, certificate=certificate_obj)
    response = HttpResponse(buffer, content_type='application/pdf')
    fname = f"certificate_{participant.student_id}_{participant.event.name.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{fname}"'
    return response


@organizer_required
def export_csv(request):
    """Export participants and certificate statuses to CSV for organizer's events."""
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="eduevent_participants.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Student ID', 'Name', 'Email', 'Event', 'Registered At',
        'Attendance Status', 'Feedback Submitted', 'Certificate ID', 'Certificate Status'
    ])

    query = Participant.objects.filter(event__organizer=request.user).select_related('event', 'certificate_record')

    for p in query.order_by('student_id'):
        cert_id = p.certificate_record.certificate_id if hasattr(p, 'certificate_record') else 'N/A'
        cert_status = p.certificate_record.status if hasattr(p, 'certificate_record') else ('Eligible' if p.eligible_for_certificate else 'Ineligible')
        writer.writerow([
            p.student_id, p.name, p.email, p.event.name,
            p.registered_at.strftime('%Y-%m-%d %H:%M'),
            'Present' if p.attendance else 'Absent',
            'Yes' if p.feedback_submitted else 'No',
            cert_id,
            cert_status,
        ])
    return response


# --- DEDICATED ADMIN MANAGEMENT VIEWS ---

@admin_required
def system_admin_dashboard(request):
    """Dedicated System Administrator Control Dashboard."""
    users_count = User.objects.count()
    events_count = Event.objects.count()
    participants_count = Participant.objects.count()
    valid_certs = Certificate.objects.filter(status='VALID').count()
    revoked_certs = Certificate.objects.filter(status='REVOKED').count()
    present_count = Participant.objects.filter(attendance=True).count()
    attendance_rate = round((present_count / participants_count * 100), 1) if participants_count > 0 else 0

    stats = {
        'total_users': users_count,
        'total_events': events_count,
        'total_participants': participants_count,
        'valid_certs': valid_certs,
        'revoked_certs': revoked_certs,
        'attendance_rate': attendance_rate,
    }

    recent_users = User.objects.select_related('profile').order_by('-date_joined')[:10]
    recent_events = Event.objects.annotate(p_count=Count('participants')).order_by('-created_at')[:5]

    return render(request, 'events/admin_dashboard.html', {
        'stats': stats,
        'recent_users': recent_users,
        'recent_events': recent_events,
    })


@admin_required
def admin_user_management(request):
    """Dedicated Admin User Role & Permissions Management view."""
    users = User.objects.select_related('profile').order_by('-date_joined')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('role')
        target_user = get_object_or_404(User, pk=user_id)
        profile, created = UserProfile.objects.get_or_create(user=target_user)
        profile.role = new_role
        profile.save()
        messages.success(request, f"Role for user '{target_user.username}' updated to {profile.get_role_display()}.")
        return redirect('admin_user_management')

    return render(request, 'events/admin_users.html', {'users': users, 'roles': UserProfile.ROLE_CHOICES})


@admin_required
def admin_event_management(request):
    """Dedicated Admin Global Event Management view."""
    events = Event.objects.annotate(p_count=Count('participants')).select_related('organizer').order_by('-date')
    return render(request, 'events/admin_events.html', {'events': events})


@admin_required
def admin_certificate_management(request):
    """Dedicated Admin Global Certificate Management & Revocation view."""
    certificates = Certificate.objects.select_related('participant', 'event', 'revoked_by').order_by('-issued_at')

    status_filter = request.GET.get('status')
    if status_filter:
        certificates = certificates.filter(status=status_filter)

    return render(request, 'events/admin_certificates.html', {'certificates': certificates, 'selected_status': status_filter})


@admin_required
def admin_revoke_certificate(request, pk):
    """Dedicated Admin endpoint to revoke ANY certificate."""
    certificate = get_object_or_404(Certificate, pk=pk)
    if request.method == 'POST':
        form = RevocationForm(request.POST)
        if form.is_valid():
            certificate.status = 'REVOKED'
            certificate.revoked_at = timezone.now()
            certificate.revocation_reason = form.cleaned_data['reason']
            certificate.revoked_by = request.user
            certificate.save()
            messages.success(request, f"Admin Action: Certificate {certificate.certificate_id} REVOKED.")
            return redirect('admin_certificate_management')
    else:
        form = RevocationForm()

    return render(request, 'events/revoke_certificate.html', {
        'participant': certificate.participant,
        'certificate': certificate,
        'form': form
    })


@admin_required
def admin_restore_certificate(request, pk):
    """Dedicated Admin endpoint to restore ANY certificate."""
    certificate = get_object_or_404(Certificate, pk=pk)
    if request.method == 'POST':
        certificate.status = 'VALID'
        certificate.revoked_at = None
        certificate.revocation_reason = ''
        certificate.save()
        messages.success(request, f"Admin Action: Certificate {certificate.certificate_id} REINSTATED.")
        return redirect('admin_certificate_management')

    return render(request, 'events/restore_certificate.html', {
        'participant': certificate.participant,
        'certificate': certificate
    })


# --- Authentication Views ---

def auth_register(request):
    """User account registration view."""
    if request.user.is_authenticated:
        return redirect(get_role_dashboard_name(request.user))

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            role = form.cleaned_data['role']
            UserProfile.objects.create(user=user, role=role)
            login(request, user)
            messages.success(request, f"Welcome to EduEvent, {user.username}!")
            return redirect(get_role_dashboard_name(user))
    else:
        form = UserRegistrationForm()

    return render(request, 'events/auth_register.html', {'form': form})


def auth_login(request):
    """User login view with strict role dashboard redirection."""
    if request.user.is_authenticated:
        return redirect(get_role_dashboard_name(request.user))

    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            messages.success(request, f"Logged in successfully. Welcome, {user.username}!")
            return redirect(get_role_dashboard_name(user))
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'events/auth_login.html')


@login_required
def auth_logout(request):
    """User logout view."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('index')
