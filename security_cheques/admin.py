"""
Admin configuration for security_cheques app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import SecurityCheque


@admin.register(SecurityCheque)
class SecurityChequeAdmin(admin.ModelAdmin):
    list_display = ('customer', 'status', 'cheque_number', 'amount', 'cheque_date', 'created_at')
    list_filter = ('status', 'cheque_date', 'created_at', 'customer__sales_person')
    search_fields = ('customer__company_name', 'cheque_number', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (_('Cheque Information'), {
            'fields': ('customer', 'status', 'cheque_number', 'amount', 'cheque_date', 'file', 'notes')
        }),
        (_('Audit Information'), {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'customer__sales_person', 'created_by', 'updated_by')