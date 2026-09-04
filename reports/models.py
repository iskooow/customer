"""
Reports models for the Customer Records Management System.
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ReportTemplate(models.Model):
    """
    Saved report templates for reuse.
    """
    name = models.CharField(_('name'), max_length=255)
    description = models.TextField(_('description'), blank=True)
    report_type = models.CharField(_('report type'), max_length=50)
    filters = models.JSONField(_('filters'), default=dict)
    columns = models.JSONField(_('columns'), default=list)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='report_templates',
        verbose_name=_('created by')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    is_public = models.BooleanField(_('public'), default=False)
    
    class Meta:
        verbose_name = _('report template')
        verbose_name_plural = _('report templates')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class ScheduledReport(models.Model):
    """
    Scheduled reports for automatic generation.
    """
    class Frequency(models.TextChoices):
        DAILY = 'daily', _('Daily')
        WEEKLY = 'weekly', _('Weekly')
        MONTHLY = 'monthly', _('Monthly')
    
    name = models.CharField(_('name'), max_length=255)
    report_template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='scheduled_reports',
        verbose_name=_('report template')
    )
    frequency = models.CharField(
        _('frequency'),
        max_length=20,
        choices=Frequency.choices
    )
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='scheduled_reports',
        verbose_name=_('recipients')
    )
    last_run = models.DateTimeField(_('last run'), null=True, blank=True)
    next_run = models.DateTimeField(_('next run'), null=True, blank=True)
    active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('scheduled report')
        verbose_name_plural = _('scheduled reports')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name