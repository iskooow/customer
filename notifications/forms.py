"""
Forms for notifications app.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import NotificationPreference


class NotificationPreferenceForm(forms.ModelForm):
    """
    Form for updating a user's notification preferences.

    The NotificationPreference model uses boolean fields for each channel/
    notification-type combination. The HTML form submits checkboxes (value
    'on' when checked) which maps naturally onto model booleans.
    """

    email_expiry_60_days = forms.BooleanField(
        required=False,
        label=_('Email: 60 days expiry'),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )
    email_expiry_30_days = forms.BooleanField(
        required=False,
        label=_('Email: 30 days expiry'),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )
    email_expiry_7_days = forms.BooleanField(
        required=False,
        label=_('Email: 7 days expiry'),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )
    email_expired = forms.BooleanField(
        required=False,
        label=_('Email: Expired'),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )
    email_missing_documents = forms.BooleanField(
        required=False,
        label=_('Email: Missing Documents'),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )
    email_cheque_pending = forms.BooleanField(
        required=False,
        label=_('Email: Cheque Pending'),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )
    in_app_expiry_60_days = forms.BooleanField(
        required=False,
        label=_('In-app: 60 days expiry'),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )
    in_app_expiry_30_days = forms.BooleanField(
        required=False,
        label=_('In-app: 30 days expiry'),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )
    in_app_expiry_7_days = forms.BooleanField(
        required=False,
        label=_('In-app: 7 days expiry'),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )
    in_app_expired = forms.BooleanField(
        required=False,
        label=_('In-app: Expired'),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )
    in_app_missing_documents = forms.BooleanField(
        required=False,
        label=_('In-app: Missing Documents'),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )
    in_app_cheque_pending = forms.BooleanField(
        required=False,
        label=_('In-app: Cheque Pending'),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )

    class Meta:
        model = NotificationPreference
        fields = [
            'email_expiry_60_days', 'email_expiry_30_days', 'email_expiry_7_days',
            'email_expired', 'email_missing_documents', 'email_cheque_pending',
            'in_app_expiry_60_days', 'in_app_expiry_30_days', 'in_app_expiry_7_days',
            'in_app_expired', 'in_app_missing_documents', 'in_app_cheque_pending',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            if isinstance(self.fields[field_name], forms.BooleanField):
                self.fields[field_name].widget.attrs.update({'class': 'form-checkbox'})