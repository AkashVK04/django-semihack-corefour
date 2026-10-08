from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),

    # Role Dashboards
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('organizer/dashboard/', views.organizer_dashboard, name='organizer_dashboard'),
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('admin/dashboard/', views.system_admin_dashboard, name='system_admin_dashboard'),

    # Dedicated Admin Management Views
    path('admin/users/', views.admin_user_management, name='admin_user_management'),
    path('admin/events/', views.admin_event_management, name='admin_event_management'),
    path('admin/certificates/', views.admin_certificate_management, name='admin_certificate_management'),
    path('admin/certificates/<int:pk>/revoke/', views.admin_revoke_certificate, name='admin_revoke_certificate'),
    path('admin/certificates/<int:pk>/restore/', views.admin_restore_certificate, name='admin_restore_certificate'),

    # Student Workflow
    path('register/', views.register, name='register'),
    path('register/success/<int:pk>/', views.registration_success, name='registration_success'),
    path('feedback/<int:pk>/', views.feedback, name='feedback'),

    # Organizer Workflow
    path('event/new/', views.create_event, name='create_event'),
    path('event/<int:pk>/edit/', views.edit_event, name='edit_event'),
    path('revoke/<int:pk>/', views.revoke_certificate, name='revoke_certificate'),
    path('restore/<int:pk>/', views.restore_certificate, name='restore_certificate'),
    path('export/csv/', views.export_csv, name='export_csv'),

    # Attendance Staff Workflow
    path('scan/', views.scan_attendance, name='scan_attendance'),
    path('mark-qr/', views.mark_qr_attendance, name='mark_qr_attendance'),

    # Public Verification & PDF Certificate
    path('verify/<str:hash>/', views.verify_certificate, name='verify_certificate'),
    path('certificate/<str:hash>/', views.certificate, name='certificate'),

    # Authentication
    path('login/', views.auth_login, name='login'),
    path('logout/', views.auth_logout, name='logout'),
    path('signup/', views.auth_register, name='signup'),
]
