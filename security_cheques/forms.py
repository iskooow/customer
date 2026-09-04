"""
Forms for security_cheques app.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import SecurityCheque


class SecurityChequeForm(forms.ModelForm):
    """Form for creating and editing security cheques."""
    
    class Meta:
        model = SecurityCheque
        fields = ['status', 'cheque_number', 'amount', 'cheque_date', 'file', 'notes']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
            'cheque_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Cheque number',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
            'cheque_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }, format='%Y-%m-%d'),
            'file': forms.FileInput(attrs={
                'class': 'form-input',
                'accept': '.pdf,.jpg,.jpeg,.png',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Optional notes...',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError(_('File size must be less than 10MB.'))
            
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            ext = file.name.lower().split('.')[-1]
            if f'.{ext}' not in allowed_extensions:
                raise forms.ValidationError(_('File type not allowed. Allowed types: PDF, JPG, PNG.'))
        
        return file
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount < 0:
            raise forms.ValidationError(_('Amount cannot be negative.'))
        return amount