from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def get_user_role(user):
    """Robust helper to retrieve the exact string role of a user."""
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'ADMIN'
    try:
        profile = getattr(user, 'profile', None)
        if profile:
            return profile.role
        from .models import UserProfile
        p = UserProfile.objects.filter(user=user).first()
        if p:
            return p.role
    except Exception:
        pass
    return 'STUDENT'


def role_required(allowed_roles=None):
    """Decorator to enforce strict role-based access control."""
    if allowed_roles is None:
        allowed_roles = []

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Please log in to access this page.")
                return redirect('login')

            user_role = get_user_role(request.user)

            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)

            messages.error(request, f"🚫 Access Denied: Restricted to {', '.join(allowed_roles)} users.")
            raise PermissionDenied
        return _wrapped_view
    return decorator


def student_required(view_func):
    """Strictly allows ONLY STUDENT users."""
    return role_required(['STUDENT'])(view_func)


def organizer_required(view_func):
    """Strictly allows ONLY EVENT_ORGANIZER users."""
    return role_required(['EVENT_ORGANIZER'])(view_func)


def staff_required(view_func):
    """Strictly allows ONLY ATTENDANCE_STAFF users."""
    return role_required(['ATTENDANCE_STAFF'])(view_func)


def admin_required(view_func):
    """Strictly allows ONLY ADMIN users or superusers."""
    return role_required(['ADMIN'])(view_func)
