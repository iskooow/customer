"""
Admin configuration for salespersons app.
"""

from django.contrib import admin
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from .models import SalesPerson


@admin.register(SalesPerson)
class SalesPersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'active', 'customer_count', 'created_at')
    list_filter = ('active', 'created_at')
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('name',)
    
    def customer_count(self, obj):
        return obj.customers.count()
    customer_count.short_description = _('Customers')
    customer_count.admin_order_field = 'customers__count'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(customers_count=Count('customers'))