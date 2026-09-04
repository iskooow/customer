"""
Security Cheque models for the Customer Records Management System.
"""

import os
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator, MinValueValidator
from customers.models import Customer


def cheque_upload_path(instance, filename):
    """Generate upload path for security cheque documents."""
    ext = filename.split('.')[-1].lower()
    cheque_id = instance.id if instance.id else uuid.uuid4().hex[:12]
    return f'customers/{instance.customer.id}/cheques/{timezone.now().strftime("%Y%m%d")}_{cheque_id}.{ext}'


class SecurityCheque(models.Model):
    """
    Security cheque model.
    """
    class Status(models.TextChoices):
        RECEIVED = 'received', _('Received')
        NOT_RECEIVED = 'not_received', _('Not Received')
        PENDING = 'pending', _('Pending')
        RETURNED = 'returned', _('Returned')
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='security_cheques',
        verbose_name=_('customer')
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_RECEIVED
    )
    cheque_number = models.CharField(_('cheque number'), max_length=100, blank=True)
    amount = models.DecimalField(
        _('amount'),
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    cheque_date = models.DateField(_('cheque date'), null=True, blank=True)
    file = models.FileField(
        _('cheque copy'),
        upload_to=cheque_upload_path,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )
    file_name = models.CharField(_('file name'), max_length=255, blank=True)
    notes = models.TextField(_('notes'), blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_cheques',
        verbose_name=_('created by')
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_cheques',
        verbose_name=_('updated by')
    )
    
    class Meta:
        verbose_name = _('security cheque')
        verbose_name_plural = _('security cheques')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['cheque_date']),
        ]
    
    def __str__(self):
        return f'{self.customer.company_name} - {self.get_status_display()}'
    
    def save(self, *args, **kwargs):
        if not self.file_name:
            if self.file:
                self.file_name = os.path.basename(self.file.name)
            else:
                self.file_name = f"cheque_{self.pk or 'new'}.pdf"
        super().save(*args, **kwargs)
    
    def get_file_extension(self):
        """Get file extension."""
        return os.path.splitext(self.file_name)[1].lower() if self.file_name else ''
    
    def is_image(self):
        """Check if file is an image."""
        return self.get_file_extension() in ['.jpg', '.jpeg', '.png']
    
    def is_pdf(self):
        """Check if file is a PDF."""
        return self.get_file_extension() == '.pdf'