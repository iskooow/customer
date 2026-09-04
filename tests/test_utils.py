"""
Tests for utility functions.
"""

import pytest
from datetime import date, timedelta

from django.test import TestCase

from customers.utils import (
    get_days_left,
    get_expiry_status,
    get_copy_status_label,
    get_copy_status_icon,
    get_copy_status_css,
    format_days_left,
    get_expiry_filter_queryset,
)


class TestExpiryUtils(TestCase):
    def test_get_days_left_future(self):
        future_date = date.today() + timedelta(days=30)
        self.assertEqual(get_days_left(future_date), 30)
    
    def test_get_days_left_today(self):
        today = date.today()
        self.assertEqual(get_days_left(today), 0)
    
    def test_get_days_left_past(self):
        past_date = date.today() - timedelta(days=10)
        self.assertEqual(get_days_left(past_date), -10)
    
    def test_get_days_left_none(self):
        self.assertIsNone(get_days_left(None))
    
    def test_get_expiry_status_valid(self):
        future_date = date.today() + timedelta(days=90)
        status = get_expiry_status(future_date)
        self.assertEqual(status['status'], 'valid')
        self.assertEqual(status['label'], 'VALID')
        self.assertEqual(status['css_class'], 'bg-green-100 text-green-700')
        self.assertEqual(status['icon'], '🟢')
    
    def test_get_expiry_status_expiring_60(self):
        future_date = date.today() + timedelta(days=45)
        status = get_expiry_status(future_date)
        self.assertEqual(status['status'], 'expiring_soon')
        self.assertEqual(status['label'], 'EXPIRING SOON')
        self.assertEqual(status['css_class'], 'bg-yellow-100 text-yellow-700')
        self.assertEqual(status['icon'], '🟡')
    
    def test_get_expiry_status_expiring_30(self):
        future_date = date.today() + timedelta(days=20)
        status = get_expiry_status(future_date)
        self.assertEqual(status['status'], 'expiring_soon')
        self.assertEqual(status['label'], 'EXPIRING SOON')
    
    def test_get_expiry_status_urgent(self):
        future_date = date.today() + timedelta(days=5)
        status = get_expiry_status(future_date)
        self.assertEqual(status['status'], 'urgent')
        self.assertEqual(status['label'], 'URGENT')
        self.assertEqual(status['css_class'], 'bg-orange-100 text-orange-700')
        self.assertEqual(status['icon'], '🟠')
    
    def test_get_expiry_status_expired(self):
        past_date = date.today() - timedelta(days=10)
        status = get_expiry_status(past_date)
        self.assertEqual(status['status'], 'expired')
        self.assertEqual(status['label'], 'EXPIRED')
        self.assertEqual(status['css_class'], 'bg-red-100 text-red-700')
        self.assertEqual(status['icon'], '🔴')
    
    def test_get_expiry_status_today(self):
        today = date.today()
        status = get_expiry_status(today)
        self.assertEqual(status['status'], 'expires_today')
        self.assertEqual(status['label'], 'EXPIRES TODAY')
    
    def test_get_expiry_status_none(self):
        status = get_expiry_status(None)
        self.assertEqual(status['status'], 'unknown')
        self.assertEqual(status['label'], 'Not Set')
    
    def test_get_copy_status_label(self):
        self.assertEqual(get_copy_status_label('complete'), 'Complete')
        self.assertEqual(get_copy_status_label('partial'), 'Partial')
        self.assertEqual(get_copy_status_label('missing'), 'Missing')
        self.assertEqual(get_copy_status_label('unknown'), 'unknown')
    
    def test_get_copy_status_icon(self):
        self.assertEqual(get_copy_status_icon('complete'), '✓')
        self.assertEqual(get_copy_status_icon('partial'), '⚠')
        self.assertEqual(get_copy_status_icon('missing'), '✕')
        self.assertEqual(get_copy_status_icon('unknown'), '✕')
    
    def test_get_copy_status_css(self):
        self.assertEqual(get_copy_status_css('complete'), 'bg-green-100 text-green-700')
        self.assertEqual(get_copy_status_css('partial'), 'bg-yellow-100 text-yellow-700')
        self.assertEqual(get_copy_status_css('missing'), 'bg-red-100 text-red-700')
        self.assertEqual(get_copy_status_css('unknown'), 'bg-gray-100 text-gray-700')
    
    def test_format_days_left(self):
        self.assertEqual(format_days_left(30), '30')
        self.assertEqual(format_days_left(0), '0')
        self.assertEqual(format_days_left(-5), 'EXPIRED')
        self.assertEqual(format_days_left(None), 'Not Set')


class TestExpiryFilterQueryset(TestCase):
    def test_get_expiry_filter_queryset(self):
        from customers.models import Customer
        from accounts.models import User
        
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
        )
        
        today = date.today()
        
        # Create customers with different expiry dates
        c1 = Customer.objects.create(
            company_name='Valid Company',
            trade_license_expiry=today + timedelta(days=90),
            created_by=user,
            updated_by=user,
        )
        c2 = Customer.objects.create(
            company_name='Expiring Soon',
            trade_license_expiry=today + timedelta(days=20),
            created_by=user,
            updated_by=user,
        )
        c3 = Customer.objects.create(
            company_name='Expired Company',
            trade_license_expiry=today - timedelta(days=10),
            created_by=user,
            updated_by=user,
        )
        c4 = Customer.objects.create(
            company_name='Urgent Company',
            trade_license_expiry=today + timedelta(days=5),
            created_by=user,
            updated_by=user,
        )
        c5 = Customer.objects.create(
            company_name='Expiring 60',
            trade_license_expiry=today + timedelta(days=45),
            created_by=user,
            updated_by=user,
        )
        
        queryset = Customer.objects.all()
        
        # Test expired filter
        expired = get_expiry_filter_queryset(queryset, 'expired', 'trade_license_expiry')
        self.assertEqual(expired.count(), 1)
        self.assertEqual(expired.first(), c3)
        
        # Test 7_days filter
        seven_days = get_expiry_filter_queryset(queryset, '7_days', 'trade_license_expiry')
        self.assertEqual(seven_days.count(), 1)
        self.assertEqual(seven_days.first(), c4)
        
        # Test 30_days filter
        thirty_days = get_expiry_filter_queryset(queryset, '30_days', 'trade_license_expiry')
        self.assertEqual(thirty_days.count(), 2)  # c2 and c4
        
        # Test 60_days filter
        sixty_days = get_expiry_filter_queryset(queryset, '60_days', 'trade_license_expiry')
        self.assertEqual(sixty_days.count(), 3)  # c2, c4, c5
        
        # Test valid filter
        valid = get_expiry_filter_queryset(queryset, 'valid', 'trade_license_expiry')
        self.assertEqual(valid.count(), 1)
        self.assertEqual(valid.first(), c1)