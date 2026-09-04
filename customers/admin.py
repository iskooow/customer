"""
Admin configuration for customers app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'company_name',
        'trade_license_number',
        'trade_license_expiry',
        'sales_person',
        'customer_status',
        'copy_status',
        'created_at',
    )
    list_filter = (
        'customer_status',
        'copy_status',
        'sales_person',
        'created_at',
        'trade_license_expiry',
        'passport_expiry',
        'eid_expiry',
    )
    search_fields = (
        'company_name',
        'trade_license_number',
        'passport_number',
        'eid_number',
        'trn',
        'sales_person__name',
    )
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (_('Company Information'), {
            'fields': ('company_name', 'trade_license_number', 'trade_license_expiry', 'trn', 'sales_person', 'customer_status', 'notes')
        }),
        (_('Passport Information'), {
            'fields': ('passport_number', 'passport_expiry')
        }),
        (_('Emirates ID Information'), {
            'fields': ('eid_number', 'eid_expiry')
        }),
        (_('Document Status'), {
            'fields': ('copy_status',)
        }),
        (_('Audit Information'), {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('sales_person', 'created_by', 'updated_by')