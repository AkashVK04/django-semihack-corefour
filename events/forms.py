from django import forms
from django.contrib.auth.models import User
from .models import Participant, Feedback, Event, Certificate, UserProfile


class UserRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ['student_id', 'name', 'email', 'event']
        widgets = {
            'student_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. CS2026001',
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'student@sjbit.edu.in',
            }),
            'event': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_student_id(self):
        sid = self.cleaned_data['student_id'].strip().upper()
        if Participant.objects.filter(student_id=sid).exists():
            raise forms.ValidationError(
                "⚠ This Student ID is already registered for an event."
            )
        return sid

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'description', 'date', 'start_time', 'end_time', 'venue', 'capacity', 'status', 'registration_deadline']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detailed Event Description'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'venue': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Main Auditorium / Seminar Hall 1'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'registration_deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['rating', 'rating_content', 'rating_speaker', 'rating_organization', 'comments']
        widgets = {
            'rating': forms.RadioSelect(attrs={'class': 'star-radio'}),
            'rating_content': forms.RadioSelect(attrs={'class': 'star-radio'}),
            'rating_speaker': forms.RadioSelect(attrs={'class': 'star-radio'}),
            'rating_organization': forms.RadioSelect(attrs={'class': 'star-radio'}),
            'comments': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience, highlights, or suggestions...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].label = 'Overall Rating'
        self.fields['rating_content'].label = 'Content Quality'
        self.fields['rating_speaker'].label = 'Speaker & Presentation'
        self.fields['rating_organization'].label = 'Event Organization'
        self.fields['comments'].label = 'Additional Comments (Optional)'
        self.fields['comments'].required = False


class RevocationForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Provide official reason for certificate revocation...',
        }),
        required=True
    )
