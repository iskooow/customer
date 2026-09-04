"""
Forms for reports app.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from salespersons.models import SalesPerson
from customers.models import Customer
from security_cheques.models import SecurityCheque


class ReportFilterForm(forms.Form):
    """Form for filtering reports."""
    
    # Date range
    date_from = forms.DateField(
        label=_('Date From'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
        })
    )
    date_to = forms.DateField(
        label=_('Date To'),
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
        })
    )
    
    # Sales person
    sales_person = forms.ModelChoiceField(
        queryset=SalesPerson.objects.filter(active=True),
        required=False,
        empty_label=_('All Sales Persons'),
        label=_('Sales Person'),
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    # Customer status
    customer_status = forms.ChoiceField(
        choices=[('', _('All'))] + Customer.CustomerStatus.choices,
        required=False,
        label=_('Customer Status'),
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    # Trade License status
    trade_license_status = forms.ChoiceField(
        choices=[
            ('', _('All')),
            ('valid', _('Valid (60+ days)')),
            ('expiring_soon', _('Expiring Soon (31-60 days)')),
            ('urgent', _('Urgent (1-30 days)')),
            ('expired', _('Expired')),
        ],
        required=False,
        label=_('Trade License Status'),
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    # Passport status
    passport_status = forms.ChoiceField(
        choices=[
            ('', _('All')),
            ('valid', _('Valid (60+ days)')),
            ('expiring_soon', _('Expiring Soon (31-60 days)')),
            ('urgent', _('Urgent (1-30 days)')),
            ('expired', _('Expired')),
        ],
        required=False,
        label=_('Passport Status'),
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    # EID status
    eid_status = forms.ChoiceField(
        choices=[
            ('', _('All')),
            ('valid', _('Valid (60+ days)')),
            ('expiring_soon', _('Expiring Soon (31-60 days)')),
            ('urgent', _('Urgent (1-30 days)')),
            ('expired', _('Expired')),
        ],
        required=False,
        label=_('EID Status'),
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    # Copy status
    copy_status = forms.ChoiceField(
        choices=[('', _('All'))] + Customer.CopyStatus.choices,
        required=False,
        label=_('Copy Status'),
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )
    
    # Security cheque status
    cheque_status = forms.ChoiceField(
        choices=[('', _('All'))] + SecurityCheque.Status.choices,
        required=False,
        label=_('Security Cheque Status'),
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )