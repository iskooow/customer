"""
Customer models for the Customer Records Management System.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse


class Customer(models.Model):
    """
    Main customer model with all required fields.
    """
    class CustomerStatus(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        PENDING = 'pending', _('Pending')
    
    class CopyStatus(models.TextChoices):
        COMPLETE = 'complete', _('Complete')
        PARTIAL = 'partial', _('Partial')
        MISSING = 'missing', _('Missing')
    
    # Maps document types to the customer expiry date field they renew.
    DOCUMENT_TYPE_EXPIRY_FIELD_MAP = {
        'trade_license': 'trade_license_expiry',
        'passport': 'passport_expiry',
        'emirates_id': 'eid_expiry',
    }
    
    # Company Information
    company_name = models.CharField(_('company name'), max_length=255, unique=True)
    trade_license_number = models.CharField(
        _('trade license number'), max_length=100, blank=True, null=True, unique=True,
    )
    trade_license_expiry = models.DateField(_('trade license expiry'), null=True, blank=True)
    trn = models.CharField(
        _('TRN'), max_length=50, blank=True, null=True, unique=True,
    )
    sales_person = models.ForeignKey(
        'salespersons.SalesPerson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers',
        verbose_name=_('sales person')
    )
    customer_status = models.CharField(
        _('customer status'),
        max_length=20,
        choices=CustomerStatus.choices,
        default=CustomerStatus.ACTIVE
    )
    notes = models.TextField(_('notes'), blank=True)
    
    # Passport Information
    passport_number = models.CharField(_('passport number'), max_length=100, blank=True)
    passport_expiry = models.DateField(_('passport expiry'), null=True, blank=True)
    
    # Emirates ID Information
    eid_number = models.CharField(_('EID number'), max_length=100, blank=True)
    eid_expiry = models.DateField(_('EID expiry'), null=True, blank=True)
    
    # Document Status
    copy_status = models.CharField(
        _('copy status'),
        max_length=20,
        choices=CopyStatus.choices,
        default=CopyStatus.MISSING
    )
    
    # Audit fields
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_customers',
        verbose_name=_('created by')
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_customers',
        verbose_name=_('updated by')
    )
    
    class Meta:
        verbose_name = _('customer')
        verbose_name_plural = _('customers')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company_name']),
            models.Index(fields=['trade_license_number']),
            models.Index(fields=['sales_person']),
            models.Index(fields=['customer_status']),
            models.Index(fields=['trade_license_expiry']),
            models.Index(fields=['passport_expiry']),
            models.Index(fields=['eid_expiry']),
        ]
    
    def __str__(self):
        return self.company_name
    
    def get_absolute_url(self):
        return reverse('customers:detail', kwargs={'pk': self.pk})
    
    def get_edit_url(self):
        return reverse('customers:edit', kwargs={'pk': self.pk})
    
    def get_delete_url(self):
        return reverse('customers:delete', kwargs={'pk': self.pk})
    
    # Expiry calculation methods
    def get_trade_license_days_left(self):
        from customers.utils import get_days_left
        if self.trade_license_expiry:
            return get_days_left(self.trade_license_expiry)
        return None
    
    def get_passport_days_left(self):
        from customers.utils import get_days_left
        if self.passport_expiry:
            return get_days_left(self.passport_expiry)
        return None
    
    def get_eid_days_left(self):
        from customers.utils import get_days_left
        if self.eid_expiry:
            return get_days_left(self.eid_expiry)
        return None
    
    def get_trade_license_status(self):
        from customers.utils import get_expiry_status
        if self.trade_license_expiry:
            return get_expiry_status(self.trade_license_expiry)
        return None
    
    def get_passport_status(self):
        from customers.utils import get_expiry_status
        if self.passport_expiry:
            return get_expiry_status(self.passport_expiry)
        return None
    
    def get_eid_status(self):
        from customers.utils import get_expiry_status
        if self.eid_expiry:
            return get_expiry_status(self.eid_expiry)
        return None
    
    def update_copy_status(self):
        """Automatically update copy status based on uploaded documents."""
        required_types = ['trade_license', 'passport', 'emirates_id', 'trn_certificate']
        uploaded_types = set(self.documents.values_list('document_type', flat=True))
        
        missing = [t for t in required_types if t not in uploaded_types]
        
        if not missing:
            self.copy_status = self.CopyStatus.COMPLETE
        elif len(missing) < len(required_types):
            self.copy_status = self.CopyStatus.PARTIAL
        else:
            self.copy_status = self.CopyStatus.MISSING
        
        self.save(update_fields=['copy_status', 'updated_at'])
    
    def sync_expiry_from_documents(self):
        """
        Update the customer's expiry date fields from the uploaded documents.

        For each document type that maps to a customer expiry field, the most
        recently uploaded document is authoritative: the customer's expiry
        date is set to that document's expiry date. Uploading a renewed
        document therefore refreshes the dashboard status (VALID), and
        uploading an expired document is respected (the status reflects the
        current document, EXPIRED). If the most recent document is deleted,
        the customer falls back to the next-most-recent upload of that type.

        Returns:
            list: The names of the expiry fields that were updated.
        """
        update_fields = []
        for doc_type, field_name in self.DOCUMENT_TYPE_EXPIRY_FIELD_MAP.items():
            latest = (
                self.documents.filter(document_type=doc_type)
                .exclude(expiry_date__isnull=True)
                .order_by('-uploaded_at', '-pk')
                .first()
            )
            current = getattr(self, field_name)
            if latest and latest.expiry_date != current:
                setattr(self, field_name, latest.expiry_date)
                update_fields.append(field_name)
        if update_fields:
            update_fields.append('updated_at')
            self.save(update_fields=update_fields)
        return update_fields
    
    def dismiss_stale_expiry_notifications(self):
        """Dismiss expiry notifications that are no longer valid.

        After a document upload/update/delete the customer's expiry fields are
        re-synced via ``sync_expiry_from_documents``.  This method then walks
        every live (UNREAD / READ) expiry notification for the customer and
        dismisses it when the underlying document type no longer falls inside
        any warning window (i.e. > 60 days away or no date at all).

        Notifications whose document type *is* still within a warning window
        are left untouched – the next ``check_expiries`` run will refresh them
        with updated messaging if needed.
        """
        from datetime import date
        from notifications.models import Notification

        today = date.today()

        # Map between the document_type stored on notifications and the
        # customer model field that holds the corresponding expiry date.
        doc_type_field_map = {
            'trade_license': 'trade_license_expiry',
            'passport': 'passport_expiry',
            'emirates_id': 'eid_expiry',
        }

        live = Notification.objects.filter(
            customer=self,
            status__in=[Notification.Status.UNREAD, Notification.Status.READ],
            document_type__in=doc_type_field_map,
        )

        to_dismiss = []
        for notif in live:
            field_name = doc_type_field_map.get(notif.document_type)
            if not field_name:
                continue
            expiry = getattr(self, field_name, None)
            if not expiry:
                # Date cleared – alert is stale.
                to_dismiss.append(notif.pk)
                continue
            days_left = (expiry - today).days
            if days_left > 60:
                # No longer within any warning window.
                to_dismiss.append(notif.pk)

        if to_dismiss:
            Notification.objects.filter(pk__in=to_dismiss).update(
                status=Notification.Status.DISMISSED,
            )

    def get_security_cheque_status(self):
        """Get the latest security cheque status."""
        cheque = self.security_cheques.first()
        if cheque:
            return cheque.get_status_display()
        return _('Not Received')
    
    def has_expired_documents(self):
        """Check if any document is expired."""
        from customers.utils import get_days_left
        from datetime import date
        
        today = date.today()
        for field in ['trade_license_expiry', 'passport_expiry', 'eid_expiry']:
            expiry = getattr(self, field)
            if expiry and expiry < today:
                return True
        return False
    
    def get_expiring_documents(self, days=30):
        """Get documents expiring within specified days."""
        from customers.utils import get_days_left
        
        expiring = []
        for field_name, label in [
            ('trade_license_expiry', 'Trade License'),
            ('passport_expiry', 'Passport'),
            ('eid_expiry', 'Emirates ID'),
        ]:
            expiry = getattr(self, field_name)
            if expiry:
                days_left = get_days_left(expiry)
                if 0 <= days_left <= days:
                    expiring.append({
                        'type': label,
                        'expiry_date': expiry,
                        'days_left': days_left,
                    })
        return expiring