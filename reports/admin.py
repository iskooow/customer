"""
Admin configuration for reports app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import ReportTemplate, ScheduledReport


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_type', 'created_by', 'is_public', 'created_at')
    list_filter = ('report_type', 'is_public', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(ScheduledReport)
class ScheduledReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_template', 'frequency', 'active', 'last_run', 'next_run')
    list_filter = ('frequency', 'active', 'created_at')
    search_fields = ('name', 'report_template__name')
    readonly_fields = ('created_at', 'updated_at', 'last_run')
    ordering = ('-created_at',)
    filter_horizontal = ('recipients',)