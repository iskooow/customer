"""
Smoke tests: every protected page must render without template errors.
Validates the modern-minimal template rebuild end to end.
"""

import pytest
from datetime import date, timedelta

from django.urls import reverse
from django.test import TestCase

from accounts.models import User
from customers.models import Customer
from salespersons.models import SalesPerson
from documents.models import Document
from security_cheques.models import SecurityCheque


@pytest.mark.django_db
class TestTemplateRenderSmoke(TestCase):
    """Render all major pages as admin to catch broken template tags/context."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com',
            username='admin',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.sales_user = User.objects.create_user(
            email='sales@example.com',
            username='sales',
            password='sales123',
            role=User.Role.SALES_PERSON,
        )
        self.sales_person = SalesPerson.objects.create(
            name='John Doe',
            email='john@example.com',
            phone='+971 50 123 4567',
        )
        self.sales_user.sales_person = self.sales_person
        self.sales_user.save()

        self.customer = Customer.objects.create(
            company_name='Test Company LLC',
            trade_license_number='123456',
            trade_license_expiry=date.today() + timedelta(days=30),
            trn='100123456789003',
            sales_person=self.sales_person,
            created_by=self.admin,
            updated_by=self.admin,
        )
        self.doc = Document.objects.create(
            customer=self.customer,
            document_type=Document.DocumentType.TRADE_LICENSE,
            file_name='trade_license.pdf',
            file_size=1024,
            uploaded_by=self.admin,
        )
        self.cheque = SecurityCheque.objects.create(
            customer=self.customer,
            status=SecurityCheque.Status.RECEIVED,
            cheque_number='CHQ123456',
            amount=10000,
            cheque_date=date.today(),
            created_by=self.admin,
            updated_by=self.admin,
        )

    def login_admin(self):
        self.client.login(email='admin@example.com', password='admin123')

    def assert_ok(self, url_name, **kwargs):
        self.login_admin()
        response = self.client.get(reverse(url_name, kwargs=kwargs or None))
        self.assertEqual(response.status_code, 200, f'{url_name} returned {response.status_code}')

    def test_accounts_pages(self):
        for url_name in [
            'accounts:profile',
            'accounts:profile_edit',
            'accounts:password_change',
            'accounts:user_list',
        ]:
            self.assert_ok(url_name)
        # User edit needs a pk
        self.assert_ok('accounts:user_edit', pk=self.sales_user.pk)

    def test_customers_pages(self):
        for url_name in [
            'customers:list',
            'customers:add',
            'customers:import',
        ]:
            self.assert_ok(url_name)
        # Import preview redirects to import when no preview exists yet
        self.login_admin()
        self.assertEqual(
            self.client.get(reverse('customers:import_preview')).status_code,
            302,
        )
        self.assert_ok('customers:detail', pk=self.customer.pk)
        self.assert_ok('customers:edit', pk=self.customer.pk)
        self.assert_ok('customers:delete', pk=self.customer.pk)
        self.assert_ok('customers:print', pk=self.customer.pk)

    def test_documents_pages(self):
        self.assert_ok('documents:list')
        self.assert_ok('documents:upload', customer_pk=self.customer.pk)
        self.assert_ok('documents:edit', pk=self.doc.pk)
        self.assert_ok('documents:delete', pk=self.doc.pk)

    def test_salespersons_pages(self):
        for url_name in ['salespersons:list', 'salespersons:add']:
            self.assert_ok(url_name)
        for url_name in [
            'salespersons:detail',
            'salespersons:edit',
            'salespersons:delete',
        ]:
            self.assert_ok(url_name, pk=self.sales_person.pk)

    def test_security_cheque_pages(self):
        self.assert_ok('security_cheques:list')
        self.assert_ok('security_cheques:add', customer_pk=self.customer.pk)
        self.assert_ok('security_cheques:edit', pk=self.cheque.pk)
        self.assert_ok('security_cheques:delete', pk=self.cheque.pk)

    def test_reports_pages(self):
        for url_name in [
            'dashboard',
            'reports:index',
            'reports:customer_report',
            'reports:expired_documents',
            'reports:expiring_documents',
            'reports:missing_documents',
            'reports:salesperson_report',
            'reports:cheque_report',
        ]:
            self.assert_ok(url_name)

    def test_audit_and_notifications_pages(self):
        for url_name in [
            'audit:list',
            'notifications:list',
            'notifications:preferences',
        ]:
            self.assert_ok(url_name)

    def test_dashboard_page(self):
        self.assert_ok('customers:list')
        self.login_admin()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)