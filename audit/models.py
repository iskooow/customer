"""
Audit log models for the Customer Records Management System.
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from customers.models import Customer


class AuditLog(models.Model):
    """
    Audit log for tracking important changes.
    """
    class Action(models.TextChoices):
        CREATED = 'created', _('Created')
        UPDATED = 'updated', _('Updated')
        DELETED = 'deleted', _('Deleted')
        DOCUMENT_UPLOADED = 'document_uploaded', _('Document Uploaded')
        DOCUMENT_UPDATED = 'document_updated', _('Document Updated')
        DOCUMENT_DELETED = 'document_deleted', _('Document Deleted')
        DOCUMENT_DOWNLOADED = 'document_downloaded', _('Document Downloaded')
        DOCUMENT_VIEWED = 'document_viewed', _('Document Viewed')
        CHEQUE_CREATED = 'cheque_created', _('Cheque Created')
        CHEQUE_UPDATED = 'cheque_updated', _('Cheque Updated')
        CHEQUE_DELETED = 'cheque_deleted', _('Cheque Deleted')
        CHEQUE_DOWNLOADED = 'cheque_downloaded', _('Cheque Downloaded')
        CHEQUE_BULK_UPDATED = 'cheque_bulk_updated', _('Cheques Bulk Updated')
        SALESPERSON_CREATED = 'salesperson_created', _('Sales Person Created')
        SALESPERSON_UPDATED = 'salesperson_updated', _('Sales Person Updated')
        SALESPERSON_DELETED = 'salesperson_deleted', _('Sales Person Deleted')
        SALESPERSON_TOGGLED = 'salesperson_toggled', _('Sales Person Toggled')
        SALESPERSON_ACTIVATED = 'salesperson_activated', _('Sales Person Activated')
        SALESPERSON_DEACTIVATED = 'salesperson_deactivated', _('Sales Person Deactivated')
        CUSTOMER_REASSIGNED = 'customer_reassigned', _('Customer Reassigned')
        IMPORTED = 'imported', _('Imported')
        EXPORTED = 'exported', _('Exported')
        BULK_UPDATED = 'bulk_updated', _('Bulk Updated')
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        verbose_name=_('user')
    )
    action = models.CharField(
        _('action'),
        max_length=30,
        choices=Action.choices
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_('customer')
    )
    description = models.TextField(_('description'))
    timestamp = models.DateTimeField(_('timestamp'), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_('IP address'), null=True, blank=True)
    user_agent = models.TextField(_('user agent'), blank=True)
    
    # Additional context fields
    object_type = models.CharField(_('object type'), max_length=50, blank=True)
    object_id = models.PositiveIntegerField(_('object ID'), null=True, blank=True)
    changes = models.JSONField(_('changes'), default=dict, blank=True)
    
    class Meta:
        verbose_name = _('audit log')
        verbose_name_plural = _('audit logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['customer', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        user_name = self.user.get_full_name() if self.user else 'System'
        customer_name = self.customer.company_name if self.customer else 'N/A'
        return f'{user_name} - {self.get_action_display()} - {customer_name} - {self.timestamp.strftime("%Y-%m-%d %H:%M")}'