"""
Forms for salespersons app.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import SalesPerson


class SalesPersonForm(forms.ModelForm):
    """Form for creating and editing sales persons."""
    
    class Meta:
        model = SalesPerson
        fields = ['name', 'email', 'phone', 'active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Full name',
                'required': True,
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'email@example.com',
                'required': True,
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+971 XX XXX XXXX',
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox',
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        qs = SalesPerson.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('A sales person with this email already exists.'))
        return email
    
    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not name:
            raise forms.ValidationError(_('Name is required.'))
        return name