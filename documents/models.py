"""
Document models for the Customer Records Management System.
"""

import os
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from customers.models import Customer


def document_upload_path(instance, filename):
    """Generate upload path for customer documents."""
    ext = filename.split('.')[-1].lower()
    return f'customers/{instance.customer.id}/documents/{instance.document_type}/{timezone.now().strftime("%Y%m%d")}_{instance.id}.{ext}'


class Document(models.Model):
    """
    Customer document model.
    """
    class DocumentType(models.TextChoices):
        TRADE_LICENSE = 'trade_license', _('Trade License')
        PASSPORT = 'passport', _('Passport')
        EMIRATES_ID = 'emirates_id', _('Emirates ID')
        TRN_CERTIFICATE = 'trn_certificate', _('TRN Certificate')
        SECURITY_CHEQUE = 'security_cheque', _('Security Cheque')
        OTHER = 'other', _('Other')
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('customer')
    )
    document_type = models.CharField(
        _('document type'),
        max_length=20,
        choices=DocumentType.choices
    )
    file = models.FileField(
        _('file'),
        upload_to=document_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'xlsx', 'xls'])]
    )
    file_name = models.CharField(_('file name'), max_length=255)
    file_size = models.PositiveIntegerField(_('file size'), default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents',
        verbose_name=_('uploaded by')
    )
    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)
    expiry_date = models.DateField(_('expiry date'), null=True, blank=True)
    notes = models.TextField(_('notes'), blank=True)
    
    class Meta:
        verbose_name = _('document')
        verbose_name_plural = _('documents')
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['customer', 'document_type']),
            models.Index(fields=['uploaded_at']),
            models.Index(fields=['expiry_date']),
        ]
    
    def __str__(self):
        return f'{self.customer.company_name} - {self.get_document_type_display()}'
    
    def save(self, *args, **kwargs):
        if self.file and not self.file_name:
            self.file_name = os.path.basename(self.file.name)
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
        
        # Update customer copy status
        self.customer.update_copy_status()
        # Keep the customer's expiry fields in sync with the uploaded document
        self.customer.sync_expiry_from_documents()
        # Dismiss expiry notifications that are no longer valid (e.g. renewed doc)
        self.customer.dismiss_stale_expiry_notifications()
    
    def delete(self, *args, **kwargs):
        customer = self.customer
        super().delete(*args, **kwargs)
        customer.update_copy_status()
        # Recompute the customer's expiry fields from the remaining documents
        customer.sync_expiry_from_documents()
        # Dismiss expiry notifications that are no longer valid
        customer.dismiss_stale_expiry_notifications()
    
    def get_file_extension(self):
        """Get file extension."""
        return os.path.splitext(self.file_name)[1].lower()
    
    def is_image(self):
        """Check if file is an image."""
        return self.get_file_extension() in ['.jpg', '.jpeg', '.png']
    
    def is_pdf(self):
        """Check if file is a PDF."""
        return self.get_file_extension() == '.pdf'
    
    def get_file_size_display(self):
        """Get human-readable file size."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'
    
    def get_days_left(self):
        """Get days left until expiry."""
        if not self.expiry_date:
            return None
        from customers.utils import get_days_left
        return get_days_left(self.expiry_date)
    
    def get_expiry_status(self):
        """Get expiry status."""
        if not self.expiry_date:
            return None
        from customers.utils import get_expiry_status
        return get_expiry_status(self.expiry_date)