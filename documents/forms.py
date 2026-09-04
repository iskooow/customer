"""
Forms for documents app.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Document
from customers.models import Customer


class DocumentForm(forms.ModelForm):
    """Form for uploading and editing documents."""
    
    class Meta:
        model = Document
        fields = ['document_type', 'file', 'expiry_date', 'notes']
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-input',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.xlsx,.xls',
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }, format='%Y-%m-%d'),
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
        
        # If customer is provided, limit document types based on what's already uploaded
        if self.customer:
            uploaded_types = set(self.customer.documents.values_list('document_type', flat=True))
            # Allow re-uploading same type (replacement)
            # But we can show which types are already uploaded
            pass
        
        # Make file required for new documents
        if not self.instance.pk:
            self.fields['file'].required = True
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (10MB max)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError(_('File size must be less than 10MB.'))
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.xlsx', '.xls']
            ext = file.name.lower().split('.')[-1]
            if f'.{ext}' not in allowed_extensions:
                raise forms.ValidationError(_('File type not allowed. Allowed types: PDF, DOC, DOCX, JPG, PNG, XLSX, XLS.'))
        
        return file
    
    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        doc_type = self.cleaned_data.get('document_type')
        
        # Auto-set expiry date from customer if not provided
        if not expiry_date and self.customer and doc_type:
            if doc_type == 'trade_license':
                expiry_date = self.customer.trade_license_expiry
            elif doc_type == 'passport':
                expiry_date = self.customer.passport_expiry
            elif doc_type == 'emirates_id':
                expiry_date = self.customer.eid_expiry
        
        return expiry_date