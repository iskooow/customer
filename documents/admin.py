"""
Admin configuration for documents app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'file_name',
        'customer',
        'document_type',
        'expiry_date',
        'uploaded_by',
        'uploaded_at',
        'file_size_display',
    )
    list_filter = (
        'document_type',
        'uploaded_at',
        'expiry_date',
        'customer__sales_person',
    )
    search_fields = (
        'file_name',
        'customer__company_name',
        'notes',
    )
    readonly_fields = ('uploaded_at', 'file_size', 'uploaded_by')
    ordering = ('-uploaded_at',)
    date_hierarchy = 'uploaded_at'
    
    fieldsets = (
        (_('Document Information'), {
            'fields': ('customer', 'document_type', 'file', 'expiry_date', 'notes')
        }),
        (_('File Information'), {
            'fields': ('file_name', 'file_size', 'uploaded_by', 'uploaded_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        return obj.get_file_size_display()
    file_size_display.short_description = _('File Size')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'customer__sales_person', 'uploaded_by')