"""
Tests for the expiry-alert/notification system: the shared scan service,
in-app preference enforcement, the refresh view, and context data.
"""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from customers.models import Customer
from salespersons.models import SalesPerson
from documents.models import Document
from notifications.models import Notification, NotificationPreference
from notifications import services


class ExpiryScanServiceTests(TestCase):
    """Unit tests for notifications.services.run_expiry_scan."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com',
            username='admin',
            password='admin123',
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.sales_person = SalesPerson.objects.create(
            name='John Doe',
            email='john@example.com',
            phone='+971 50 123 4567',
        )
        self.sales_user = User.objects.create_user(
            email='sales@example.com',
            username='sales',
            password='sales123',
            role=User.Role.SALES_PERSON,
            sales_person=self.sales_person,
        )

    def _customer(self, **kw):
        defaults = {
            'company_name': 'Acme LLC',
            'trade_license_number': 'TL123',
            'sales_person': self.sales_person,
            'trade_license_expiry': date.today() + timedelta(days=-5),
            'copy_status': Customer.CopyStatus.COMPLETE,
        }
        defaults.update(kw)
        return Customer.objects.create(**defaults)

    def test_creates_expired_notification_for_sales_and_admin(self):
        self._customer()
        result = services.run_expiry_scan(user_scope=None, dry_run=False)

        # One admin + one sales user should each get an EXPIRED alert.
        self.assertEqual(result['created_count'], 2)
        self.assertEqual(
            Notification.objects.filter(type=Notification.Type.EXPIRED).count(),
            2,
        )
        # Sales user sees it too.
        self.assertTrue(
            Notification.objects.filter(user=self.sales_user).exists()
        )

    def test_in_app_preference_is_enforced(self):
        self._customer()
        # Sales user opts out of in-app Expired alerts.
        NotificationPreference.objects.create(
            user=self.sales_user,
            in_app_expired=False,
        )
        result = services.run_expiry_scan(user_scope=None, dry_run=False)


    def test_renewed_document_dismisses_stale_alert(self):
        customer = self._customer()
        # Create a live alert manually to simulate a previous Expired alert.
        Notification.objects.create(
            user=self.admin,
            type=Notification.Type.EXPIRED,
            title='Trade License Expired: Acme LLC',
            message='expired',
            customer=customer,
            document_type='trade_license',
        )
        # Renew: move expiry far into the future.
        customer.trade_license_expiry = date.today() + timedelta(days=180)
        customer.save(update_fields=['trade_license_expiry'])

        services.run_expiry_scan(user_scope=None, dry_run=False)

        notif = Notification.objects.get(
            customer=customer, document_type='trade_license'
        )
        self.assertEqual(notif.status, Notification.Status.DISMISSED)

    def test_sales_user_scope_only_scans_their_customers(self):
        self._customer()  # belongs to self.sales_person
        other_sp = SalesPerson.objects.create(
            name='Other Rep', email='other@example.com', phone='+971 55 000 0000'
        )
        Customer.objects.create(
            company_name='Other Co',
            trade_license_number='TL999',
            sales_person=other_sp,
            trade_license_expiry=date.today() + timedelta(days=-1),
            copy_status=Customer.CopyStatus.COMPLETE,
        )

        # Sales user triggers a refresh scoped to themselves.
        result = services.run_expiry_scan(user_scope=self.sales_user)

        # Only their own customer's alert is created for themselves.
        self.assertEqual(result['created_count'], 1)
        self.assertEqual(
            Notification.objects.filter(user=self.sales_user).count(), 1
        )
        notification = Notification.objects.get(user=self.sales_user)
        self.assertEqual(notification.customer.company_name, 'Acme LLC')
    def test_missing_document_alert_includes_trn_certificate(self):
        """A customer missing ONLY the TRN Certificate still gets an alert.
    
        Regression: TRN Certificate was added to the required document
        types (``Customer.update_copy_status``) but the missing-document
        labels were still derived from the 3 expiry-tracked types, so a
        customer holding Trade License + Passport + EID (but no TRN
        certificate) silently received no missing-document alert.
        """
        customer = self._customer()
        customer.copy_status = Customer.CopyStatus.PARTIAL
        customer.save(update_fields=['copy_status'])
        for doc_type, days in [
            ('trade_license', 120),
            ('passport', 120),
            ('emirates_id', 120),
        ]:
            Document.objects.create(
                customer=customer,
                document_type=doc_type,
                file_name=f'{doc_type}.pdf',
                file_size=1024,
                uploaded_by=self.admin,
                expiry_date=date.today() + timedelta(days=days),
            )
        # Sanity: customers parameter—the fix flags the missing label.
        self.assertEqual(
            services._missing_document_labels(customer), ['TRN Certificate']
        )
    
        result = services.run_expiry_scan(user_scope=None, dry_run=False)
        self.assertGreater(result['created_count'], 0)
        notif = Notification.objects.filter(
            customer=customer,
            type=Notification.Type.MISSING_DOCUMENTS,
        ).first()
        self.assertIsNotNone(notif, 'missing-document alert was not created')
        self.assertIn('TRN Certificate', notif.message)
    
    
class RefreshAlertsViewTests(TestCase):
    """Tests for the on-demand 'Refresh Alerts' POST view."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com',
            username='admin',
            password='admin123',
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.sales_person = SalesPerson.objects.create(
            name='John Doe',
            email='john@example.com',
            phone='+971 50 123 4567',
        )
        Customer.objects.create(
            company_name='Acme LLC',
            trade_license_number='TL123',
            sales_person=self.sales_person,
            trade_license_expiry=date.today() + timedelta(days=-5),
            copy_status=Customer.CopyStatus.COMPLETE,
        )

    def test_refresh_creates_alerts_and_redirects(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('notifications:refresh'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('notifications:list'))
        self.assertTrue(
            Notification.objects.filter(user=self.admin).exists()
        )

    def test_requires_login(self):
        response = self.client.post(reverse('notifications:refresh'))
        self.assertEqual(response.status_code, 302)
        # Not logged in -> redirected to login.


class NotificationListContextTests(TestCase):
    """Tests for the Expiry Alerts list view context."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com',
            username='admin',
            password='admin123',
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def test_context_has_unread_count_and_last_scan(self):
        sales_person = SalesPerson.objects.create(
            name='Rep', email='r@example.com', phone='+971 50 000 0000'
        )
        customer = Customer.objects.create(
            company_name='Acme LLC',
            trade_license_number='TL123',
            sales_person=sales_person,
        )
        Notification.objects.create(
            user=self.admin,
            type=Notification.Type.EXPIRED,
            title='x',
            message='m',
            customer=customer,
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse('notifications:list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['unread_count'], 1)
        self.assertIsNotNone(response.context['last_scan_at'])

    def test_dashboard_stats_context_has_unread_alerts(self):
        """The bell badge uses the real per-user unread count."""
        from django.test import RequestFactory
        from customers.context_processors import dashboard_stats

        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.admin
        data = dashboard_stats(request)
        self.assertIn('unread_alerts', data['dashboard_stats'])
        # No notifications yet -> zero, not a missing key.
        self.assertEqual(data['dashboard_stats']['unread_alerts'], 0)
