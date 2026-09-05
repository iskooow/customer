"""
Forms for customers app.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Customer
from salespersons.models import SalesPerson


class CustomerForm(forms.ModelForm):
    """Form for creating and editing customers."""
    
    class Meta:
        model = Customer
        fields = [
            'company_name',
            'trade_license_number',
            'trade_license_expiry',
            'trn',
            'sales_person',
            'customer_status',
            'notes',
            'passport_number',
            'passport_expiry',
            'eid_number',
            'eid_expiry',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter company name',
                'required': True,
            }),
            'trade_license_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Trade license number',
            }),
            'trade_license_expiry': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }, format='%Y-%m-%d'),
            'trn': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Tax Registration Number',
            }),
            'sales_person': forms.Select(attrs={
                'class': 'form-select',
            }),
            'customer_status': forms.Select(attrs={
                'class': 'form-select',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': 'Additional notes...',
            }),
            'passport_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Passport number',
            }),
            'passport_expiry': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }, format='%Y-%m-%d'),
            'eid_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Emirates ID number (e.g., 784-XXXX-XXXXXXX-X)',
            }),
            'eid_expiry': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }, format='%Y-%m-%d'),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Limit sales person choices based on user role
        if self.user and not self.user.is_admin_user:
            if hasattr(self.user, 'sales_person') and self.user.sales_person:
                self.fields['sales_person'].queryset = SalesPerson.objects.filter(pk=self.user.sales_person.pk)
                self.fields['sales_person'].initial = self.user.sales_person
                self.fields['sales_person'].widget.attrs['disabled'] = 'disabled'
            else:
                self.fields['sales_person'].queryset = SalesPerson.objects.none()
        else:
            self.fields['sales_person'].queryset = SalesPerson.objects.filter(active=True)
        
        self.fields['sales_person'].empty_label = _('--- Select Sales Person ---')
        
        # Make company_name required
        self.fields['company_name'].required = True
    
    def clean_company_name(self):
        company_name = self.cleaned_data['company_name'].strip()
        if not company_name:
            raise forms.ValidationError(_('Company name is required.'))
        
        # Check for duplicates (excluding current instance)
        qs = Customer.objects.filter(company_name__iexact=company_name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('A customer with this company name already exists.'))
        
        return company_name
    
    def clean_trade_license_number(self):
        trade_license = (self.cleaned_data.get('trade_license_number') or '').strip()
        if trade_license:
            qs = Customer.objects.filter(trade_license_number__iexact=trade_license)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(_('A customer with this trade license number already exists.'))
        return trade_license or None

    def clean_trn(self):
        trn = (self.cleaned_data.get('trn') or '').strip()
        if trn:
            qs = Customer.objects.filter(trn__iexact=trn)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(_('A customer with this TRN already exists.'))
        return trn or None
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            if not instance.pk:
                instance.created_by = self.user
            instance.updated_by = self.user
        if commit:
            instance.save()
            # Update copy status based on documents
            instance.update_copy_status()
            # Reconcile the customer's expiry fields with the uploaded documents.
            # The most recently uploaded document is authoritative, so a saved
            # form cannot leave an expiry that disagrees with the customer's
            # current documents (e.g. a document-uploaded renewal would be
            # clobbered by a stale manual value).
            instance.sync_expiry_from_documents()
            # Dismiss expiry notifications that are no longer valid
            instance.dismiss_stale_expiry_notifications()
        return instance


class CustomerFilterForm(forms.Form):
    """Form for filtering customers."""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Search by name, license, passport, EID, TRN, sales person...',
            'hx-get': '.',
            'hx-trigger': 'keyup changed delay:300ms',
            'hx-target': '#customer-table',
            'hx-indicator': '#search-spinner',
        })
    )
    
    sales_person = forms.ModelChoiceField(
        queryset=SalesPerson.objects.filter(active=True),
        required=False,
        empty_label=_('All Sales Persons'),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '.',
            'hx-trigger': 'change',
            'hx-target': '#customer-table',
            'hx-indicator': '#filter-spinner',
        })
    )
    
    customer_status = forms.ChoiceField(
        choices=[('', _('All Statuses'))] + Customer.CustomerStatus.choices,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '.',
            'hx-trigger': 'change',
            'hx-target': '#customer-table',
            'hx-indicator': '#filter-spinner',
        })
    )
    
    document_status = forms.ChoiceField(
        choices=[
            ('', _('All Documents')),
            ('expired', _('Expired Documents')),
            ('7_days', _('Expiring Within 7 Days')),
            ('30_days', _('Expiring Within 30 Days')),
            ('60_days', _('Expiring Within 60 Days')),
            ('missing', _('Missing Documents')),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '.',
            'hx-trigger': 'change',
            'hx-target': '#customer-table',
            'hx-indicator': '#filter-spinner',
        })
    )
    
    copy_status = forms.ChoiceField(
        choices=[('', _('All Copy Status'))] + Customer.CopyStatus.choices,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '.',
            'hx-trigger': 'change',
            'hx-target': '#customer-table',
            'hx-indicator': '#filter-spinner',
        })
    )
    
    cheque_status = forms.ChoiceField(
        choices=[
            ('', _('All Cheque Status')),
            ('received', _('Received')),
            ('pending', _('Pending')),
            ('not_received', _('Not Received')),
            ('returned', _('Returned')),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-get': '.',
            'hx-trigger': 'change',
            'hx-target': '#customer-table',
            'hx-indicator': '#filter-spinner',
        })
    )


class CustomerImportForm(forms.Form):
    """Form for Excel import."""
    
    excel_file = forms.FileField(
        label=_('Excel File'),
        help_text=_('Upload an Excel file (.xlsx) with customer data.'),
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': '.xlsx',
        })
    )
    
    def clean_excel_file(self):
        file = self.cleaned_data['excel_file']
        if not file.name.lower().endswith('.xlsx'):
            raise forms.ValidationError(_('File must be an Excel file (.xlsx).'))
        if file.size > 10 * 1024 * 1024:  # 10MB
            raise forms.ValidationError(_('File size must be less than 10MB.'))
        return file