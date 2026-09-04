"""
Forms for accounts app.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

from .models import User


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label=_('Email'),
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'user@example.com'})
    )
    username = forms.CharField(
        label=_('Username'),
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'username'})
    )
    first_name = forms.CharField(
        label=_('First Name'),
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        label=_('Last Name'),
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'})
    )
    role = forms.ChoiceField(
        label=_('Role'),
        choices=User.Role.choices,
        initial=User.Role.SALES_PERSON,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    phone = forms.CharField(
        label=_('Phone'),
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+971 XX XXX XXXX'})
    )
    
    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'role', 'phone', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Confirm Password'})
    
    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_('A user with this email already exists.'))
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        user.role = self.cleaned_data['role']
        user.phone = self.cleaned_data['phone']
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('logo', 'first_name', 'last_name', 'phone', 'email')
        widgets = {
            'logo': forms.ClearableFileInput(attrs={
                'class': 'form-input',
                'accept': 'image/png,image/jpeg,image/gif,image/webp,image/svg+xml',
            }),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+971 XX XXX XXXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
        }

    MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5 MB

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if not logo:
            return logo
        # ClearableFileInput can submit False when "clear" checkbox is ticked
        if logo in (False, None):
            return logo
        if logo.size > self.MAX_LOGO_SIZE:
            raise forms.ValidationError(
                _('The logo file is too large (%.1f MB). Maximum allowed is 5 MB.') % (logo.size / (1024 * 1024))
            )
        return logo

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError(_('A user with this email already exists.'))
        return email


class UserUpdateForm(UserChangeForm):
    password = None
    
    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'role', 'phone', 'is_active', 'is_staff', 'sales_person')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+971 XX XXX XXXX'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'sales_person': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sales_person'].queryset = self.fields['sales_person'].queryset.filter(active=True)
        self.fields['sales_person'].required = False
        self.fields['sales_person'].empty_label = _('--- Select Sales Person ---')