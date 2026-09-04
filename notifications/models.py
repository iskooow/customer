"""
Notifications models for the Customer Records Management System.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from customers.models import Customer


class Notification(models.Model):
    """
    Notification model for expiry alerts and other notifications.
    """
    class Type(models.TextChoices):
        EXPIRY_60_DAYS = 'expiry_60_days', _('Expiring in 60 Days')
        EXPIRY_30_DAYS = 'expiry_30_days', _('Expiring in 30 Days')
        EXPIRY_7_DAYS = 'expiry_7_days', _('Expiring in 7 Days')
        EXPIRED = 'expired', _('Expired')
        MISSING_DOCUMENTS = 'missing_documents', _('Missing Documents')
        CHEQUE_PENDING = 'cheque_pending', _('Cheque Pending')
    
    class Status(models.TextChoices):
        UNREAD = 'unread', _('Unread')
        READ = 'read', _('Read')
        DISMISSED = 'dismissed', _('Dismissed')
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('user')
    )
    type = models.CharField(
        _('type'),
        max_length=30,
        choices=Type.choices
    )
    title = models.CharField(_('title'), max_length=255)
    message = models.TextField(_('message'))
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name=_('customer')
    )
    document_type = models.CharField(_('document type'), max_length=50, blank=True)
    expiry_date = models.DateField(_('expiry date'), null=True, blank=True)
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.UNREAD
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    read_at = models.DateTimeField(_('read at'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', '-created_at']),
            models.Index(fields=['customer', '-created_at']),
        ]
    
    def __str__(self):
        return f'{self.user} - {self.get_type_display()} - {self.title}'
    
    def mark_as_read(self):
        if self.status == self.Status.UNREAD:
            self.status = self.Status.READ
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])
    
    def dismiss(self):
        if self.status != self.Status.DISMISSED:
            self.status = self.Status.DISMISSED
            self.save(update_fields=['status'])


class NotificationPreference(models.Model):
    """
    User notification preferences.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name=_('user')
    )
    email_expiry_60_days = models.BooleanField(_('Email: 60 days expiry'), default=True)
    email_expiry_30_days = models.BooleanField(_('Email: 30 days expiry'), default=True)
    email_expiry_7_days = models.BooleanField(_('Email: 7 days expiry'), default=True)
    email_expired = models.BooleanField(_('Email: Expired'), default=True)
    email_missing_documents = models.BooleanField(_('Email: Missing Documents'), default=True)
    email_cheque_pending = models.BooleanField(_('Email: Cheque Pending'), default=True)
    in_app_expiry_60_days = models.BooleanField(_('In-app: 60 days expiry'), default=True)
    in_app_expiry_30_days = models.BooleanField(_('In-app: 30 days expiry'), default=True)
    in_app_expiry_7_days = models.BooleanField(_('In-app: 7 days expiry'), default=True)
    in_app_expired = models.BooleanField(_('In-app: Expired'), default=True)
    in_app_missing_documents = models.BooleanField(_('In-app: Missing Documents'), default=True)
    in_app_cheque_pending = models.BooleanField(_('In-app: Cheque Pending'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('notification preference')
        verbose_name_plural = _('notification preferences')
    
    def __str__(self):
        return f'{self.user} - Preferences'