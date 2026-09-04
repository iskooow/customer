"""
Admin configuration for audit app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'customer', 'description_short')
    list_filter = ('action', 'timestamp', 'user')
    search_fields = ('description', 'user__email', 'user__first_name', 'user__last_name', 'customer__company_name')
    readonly_fields = ('user', 'action', 'customer', 'description', 'timestamp', 'ip_address', 'user_agent', 'object_type', 'object_id', 'changes')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    
    def description_short(self, obj):
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
    description_short.short_description = _('Description')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'customer')