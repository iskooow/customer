"""
SalesPerson models for the Customer Records Management System.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class SalesPerson(models.Model):
    """
    Sales person model.
    """
    name = models.CharField(_('name'), max_length=255)
    email = models.EmailField(_('email'), unique=True)
    phone = models.CharField(_('phone'), max_length=20, blank=True)
    active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('sales person')
        verbose_name_plural = _('sales persons')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_customer_count(self):
        return self.customers.count()
    
    def get_expired_documents_count(self):
        from customers.utils import get_days_left
        from datetime import date
        
        count = 0
        today = date.today()
        for customer in self.customers.all():
            for field in ['trade_license_expiry', 'passport_expiry', 'eid_expiry']:
                expiry = getattr(customer, field)
                if expiry and expiry < today:
                    count += 1
        return count
    
    def get_expiring_soon_count(self, days=30):
        from customers.utils import get_days_left
        
        count = 0
        for customer in self.customers.all():
            for field in ['trade_license_expiry', 'passport_expiry', 'eid_expiry']:
                expiry = getattr(customer, field)
                if expiry:
                    days_left = get_days_left(expiry)
                    if 0 <= days_left <= days:
                        count += 1
        return count
    
    def get_missing_documents_count(self):
        count = 0
        for customer in self.customers.all():
            if customer.copy_status != customer.CopyStatus.COMPLETE:
                count += 1
        return count
    
    def get_pending_cheques_count(self):
        return self.customers.filter(security_cheques__status__in=['pending', 'not_received']).distinct().count()