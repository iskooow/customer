"""
Tests for models.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from customers.models import Customer
from salespersons.models import SalesPerson
from documents.models import Document
from security_cheques.models import SecurityCheque
from notifications.models import Notification


@pytest.mark.django_db
class TestCustomerModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )
        
        self.sales_person = SalesPerson.objects.create(
            name='John Doe',
            email='john@example.com',
            phone='+971 50 123 4567',
        )
    
    def test_customer_creation(self):
        customer = Customer.objects.create(
            company_name='Test Company LLC',
            trade_license_number='123456',
            trade_license_expiry=date.today() + timedelta(days=30),
            trn='100123456789003',
            sales_person=self.sales_person,
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.assertEqual(customer.company_name, 'Test Company LLC')
        self.assertEqual(customer.trade_license_number, '123456')
        self.assertEqual(customer.sales_person, self.sales_person)
        self.assertEqual(customer.customer_status, Customer.CustomerStatus.ACTIVE)
        self.assertEqual(customer.copy_status, Customer.CopyStatus.MISSING)
    
    def test_trade_license_days_left(self):
        future_date = date.today() + timedelta(days=30)
        customer = Customer.objects.create(
            company_name='Test Company LLC',
            trade_license_expiry=future_date,
            created_by=self.user,
            updated_by=self.user,
        )
        
        days_left = customer.get_trade_license_days_left()
        self.assertEqual(days_left, 30)
    
    def test_expired_trade_license(self):
        past_date = date.today() - timedelta(days=10)
        customer = Customer.objects.create(
            company_name='Test Company LLC',
            trade_license_expiry=past_date,
            created_by=self.user,
            updated_by=self.user,
        )
        
        days_left = customer.get_trade_license_days_left()
        self.assertEqual(days_left, -10)
        
        status = customer.get_trade_license_status()
        self.assertEqual(status['status'], 'expired')
        self.assertEqual(status['label'], 'EXPIRED')
    
    def test_expiring_soon_status(self):
        soon_date = date.today() + timedelta(days=15)
        customer = Customer.objects.create(
            company_name='Test Company LLC',
            trade_license_expiry=soon_date,
            created_by=self.user,
            updated_by=self.user,
        )
        
        status = customer.get_trade_license_status()
        self.assertEqual(status['status'], 'expiring_soon')
        self.assertEqual(status['label'], 'EXPIRING SOON')
    
    def test_urgent_status(self):
        urgent_date = date.today() + timedelta(days=5)
        customer = Customer.objects.create(
            company_name='Test Company LLC',
            trade_license_expiry=urgent_date,
            created_by=self.user,
            updated_by=self.user,
        )
        
        status = customer.get_trade_license_status()
        self.assertEqual(status['status'], 'urgent')
        self.assertEqual(status['label'], 'URGENT')
    
    def test_valid_status(self):
        valid_date = date.today() + timedelta(days=90)
        customer = Customer.objects.create(
            company_name='Test Company LLC',
            trade_license_expiry=valid_date,
            created_by=self.user,
            updated_by=self.user,
        )
        
        status = customer.get_trade_license_status()
        self.assertEqual(status['status'], 'valid')
        self.assertEqual(status['label'], 'VALID')
    
    def test_update_copy_status(self):
        customer = Customer.objects.create(
            company_name='Test Company LLC',
            created_by=self.user,
            updated_by=self.user,
        )
        
        # Initially missing
        self.assertEqual(customer.copy_status, Customer.CopyStatus.MISSING)
        
        # Add trade license
        Document.objects.create(
            customer=customer,
            document_type=Document.DocumentType.TRADE_LICENSE,
            file_name='trade_license.pdf',
            file_size=1000,
            uploaded_by=self.user,
        )
        customer.refresh_from_db()
        self.assertEqual(customer.copy_status, Customer.CopyStatus.PARTIAL)
        
        # Add passport
        Document.objects.create(
            customer=customer,
            document_type=Document.DocumentType.PASSPORT,
            file_name='passport.pdf',
            file_size=1000,
            uploaded_by=self.user,
        )
        customer.refresh_from_db()
        self.assertEqual(customer.copy_status, Customer.CopyStatus.PARTIAL)
        
        # Add EID
        Document.objects.create(
            customer=customer,
            document_type=Document.DocumentType.EMIRATES_ID,
            file_name='eid.pdf',
            file_size=1000,
            uploaded_by=self.user,
        )
        customer.refresh_from_db()
        # TRN Certificate is also required, so still partial
        self.assertEqual(customer.copy_status, Customer.CopyStatus.PARTIAL)

        # Add TRN Certificate
        Document.objects.create(
            customer=customer,
            document_type=Document.DocumentType.TRN_CERTIFICATE,
            file_name='trn_certificate.pdf',
            file_size=1000,
            uploaded_by=self.user,
        )
        customer.refresh_from_db()
        self.assertEqual(customer.copy_status, Customer.CopyStatus.COMPLETE)


@pytest.mark.django_db
class TestSalesPersonModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
        )
    
    def test_sales_person_creation(self):
        sp = SalesPerson.objects.create(
            name='John Doe',
            email='john@example.com',
            phone='+971 50 123 4567',
        )
        
        self.assertEqual(sp.name, 'John Doe')
        self.assertEqual(sp.email, 'john@example.com')
        self.assertTrue(sp.active)
    
    def test_get_customer_count(self):
        sp = SalesPerson.objects.create(
            name='John Doe',
            email='john@example.com',
        )
        
        customer = Customer.objects.create(
            company_name='Test Company LLC',
            sales_person=sp,
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.assertEqual(sp.get_customer_count(), 1)
    
    def test_expired_documents_count(self):
        sp = SalesPerson.objects.create(
            name='John Doe',
            email='john@example.com',
        )
        
        # Create customer with expired trade license
        customer = Customer.objects.create(
            company_name='Test Company LLC',
            trade_license_expiry=date.today() - timedelta(days=10),
            sales_person=sp,
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.assertEqual(sp.get_expired_documents_count(), 1)


@pytest.mark.django_db
class TestSecurityChequeModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
        )
        
        self.sales_person = SalesPerson.objects.create(
            name='John Doe',
            email='john@example.com',
        )
        
        self.customer = Customer.objects.create(
            company_name='Test Company LLC',
            sales_person=self.sales_person,
            created_by=self.user,
            updated_by=self.user,
        )
    
    def test_security_cheque_creation(self):
        cheque = SecurityCheque.objects.create(
            customer=self.customer,
            status=SecurityCheque.Status.RECEIVED,
            cheque_number='CHQ123456',
            amount=Decimal('10000.00'),
            cheque_date=date.today(),
            created_by=self.user,
            updated_by=self.user,
        )
        
        self.assertEqual(cheque.status, SecurityCheque.Status.RECEIVED)
        self.assertEqual(cheque.amount, Decimal('10000.00'))
        self.assertEqual(str(cheque), f'{self.customer.company_name} - Received')
    
    def test_cheque_status_choices(self):
        self.assertEqual(SecurityCheque.Status.RECEIVED, 'received')
        self.assertEqual(SecurityCheque.Status.NOT_RECEIVED, 'not_received')
        self.assertEqual(SecurityCheque.Status.PENDING, 'pending')
        self.assertEqual(SecurityCheque.Status.RETURNED, 'returned')


@pytest.mark.django_db
class TestDocumentModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
        )
        
        self.customer = Customer.objects.create(
            company_name='Test Company LLC',
            created_by=self.user,
            updated_by=self.user,
        )
    
    def test_document_creation(self):
        doc = Document.objects.create(
            customer=self.customer,
            document_type=Document.DocumentType.TRADE_LICENSE,
            file_name='trade_license.pdf',
            file_size=1024,
            uploaded_by=self.user,
        )
        
        self.assertEqual(doc.document_type, Document.DocumentType.TRADE_LICENSE)
        self.assertEqual(doc.file_name, 'trade_license.pdf')
        self.assertEqual(doc.customer, self.customer)
    
    def test_get_file_size_display(self):
        doc = Document.objects.create(
            customer=self.customer,
            document_type=Document.DocumentType.TRADE_LICENSE,
            file_name='trade_license.pdf',
            file_size=1024 * 1024 * 2,  # 2 MB
            uploaded_by=self.user,
        )
        
        self.assertEqual(doc.get_file_size_display(), '2.0 MB')
    
    def test_document_expiry_syncs_customer_expiry(self):
        """Uploading a document with a future expiry date refreshes the
        customer's expiry field so the dashboard no longer shows EXPIRED."""
        past = date.today() - timedelta(days=30)
        self.customer.trade_license_expiry = past
        self.customer.save(update_fields=['trade_license_expiry', 'updated_at'])
        
        future = date.today() + timedelta(days=120)
        Document.objects.create(
            customer=self.customer,
            document_type=Document.DocumentType.TRADE_LICENSE,
            file_name='renewed_license.pdf',
            file_size=1024,
            expiry_date=future,
            uploaded_by=self.user,
        )
        
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.trade_license_expiry, future)
        self.assertGreater(self.customer.get_trade_license_days_left(), 0)
    
    def test_document_expiry_is_authoritative(self):
        """The most recently uploaded document is authoritative, even if it is
        expired: uploading an expired document must make the customer's expiry
        reflect it (so the dashboard shows EXPIRED), not keep a stale valid date."""
        valid = date.today() + timedelta(days=300)
        self.customer.trade_license_expiry = valid
        self.customer.save(update_fields=['trade_license_expiry', 'updated_at'])

        # A first, older, still-valid scan...
        Document.objects.create(
            customer=self.customer,
            document_type=Document.DocumentType.TRADE_LICENSE,
            file_name='old_license.pdf',
            file_size=1024,
            expiry_date=date.today() + timedelta(days=30),
            uploaded_by=self.user,
        )
        # ...followed by the most recent upload: an EXPIRED license.
        expired = date.today() - timedelta(days=90)
        Document.objects.create(
            customer=self.customer,
            document_type=Document.DocumentType.TRADE_LICENSE,
            file_name='current_expired_license.pdf',
            file_size=1024,
            expiry_date=expired,
            uploaded_by=self.user,
        )

        self.customer.refresh_from_db()
        # The latest upload wins, even though it is expired.
        self.assertEqual(self.customer.trade_license_expiry, expired)
        self.assertLess(self.customer.get_trade_license_days_left(), 0)
    
    def test_document_delete_falls_back_to_previous_document(self):
        """Deleting the most recent document falls back to the next-most-recent
        upload of that type, rather than preserving the deleted document's date."""
        older = date.today() + timedelta(days=60)
        newer = date.today() + timedelta(days=200)
        Document.objects.create(
            customer=self.customer,
            document_type=Document.DocumentType.PASSPORT,
            file_name='passport_old.pdf',
            file_size=1024,
            expiry_date=older,
            uploaded_by=self.user,
        )
        latest_doc = Document.objects.create(
            customer=self.customer,
            document_type=Document.DocumentType.PASSPORT,
            file_name='passport_new.pdf',
            file_size=1024,
            expiry_date=newer,
            uploaded_by=self.user,
        )

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.passport_expiry, newer)

        latest_doc.delete()
        self.customer.refresh_from_db()
        # Falls back to the remaining (older) passport document.
        self.assertEqual(self.customer.passport_expiry, older)

    def test_renewing_document_dismisses_stale_expiry_notification(self):
        """Renewing an expired document automatically dismisses the old
        Expired/Expiring-soon notification so it no longer appears in the
        Expiry Alerts tab."""
        # Simulate an "Expired" alert created for the current trade license.
        past = date.today() - timedelta(days=30)
        self.customer.trade_license_expiry = past
        self.customer.save(update_fields=['trade_license_expiry', 'updated_at'])

        Document.objects.create(
            customer=self.customer,
            document_type=Document.DocumentType.TRADE_LICENSE,
            file_name='expired_license.pdf',
            file_size=1024,
            expiry_date=past,
            uploaded_by=self.user,
        )

        Notification.objects.create(
            user=self.user,
            type=Notification.Type.EXPIRED,
            title='Trade License Expired: Test Company LLC',
            message='The trade license for Test Company LLC expired on ...',
            customer=self.customer,
            document_type='trade_license',
            expiry_date=past,
        )

        # Upload a renewed license with a far-future expiry.
        future = date.today() + timedelta(days=180)
        Document.objects.create(
            customer=self.customer,
            document_type=Document.DocumentType.TRADE_LICENSE,
            file_name='renewed_license.pdf',
            file_size=1024,
            expiry_date=future,
            uploaded_by=self.user,
        )

        # The stale alert must have been dismissed automatically.
        notif = Notification.objects.get(customer=self.customer, document_type='trade_license')
        self.assertEqual(notif.status, Notification.Status.DISMISSED)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.trade_license_expiry, future)

    def test_expired_document_keeps_expiry_notification(self):
        """If the latest document is still expired / within a warning window,
        the live notification must NOT be dismissed."""
        past = date.today() - timedelta(days=40)
        Document.objects.create(
            customer=self.customer,
            document_type=Document.DocumentType.EMIRATES_ID,
            file_name='eid_expired.pdf',
            file_size=1024,
            expiry_date=past,
            uploaded_by=self.user,
        )

        Notification.objects.create(
            user=self.user,
            type=Notification.Type.EXPIRED,
            title='Emirates ID Expired: Test Company LLC',
            message='The Emirates ID for Test Company LLC expired on ...',
            customer=self.customer,
            document_type='emirates_id',
            expiry_date=past,
        )

        # Uploading another still-expired document should not dismiss the alert.
        Document.objects.create(
            customer=self.customer,
            document_type=Document.DocumentType.EMIRATES_ID,
            file_name='eid_expired_v2.pdf',
            file_size=1024,
            expiry_date=past,
            uploaded_by=self.user,
        )

        notif = Notification.objects.get(customer=self.customer, document_type='emirates_id')
        self.assertEqual(notif.status, Notification.Status.UNREAD)


@pytest.mark.django_db
class TestUserModel(TestCase):
    def test_user_creation(self):
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role=User.Role.SALES_PERSON,
        )
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.role, User.Role.SALES_PERSON)
        self.assertTrue(user.check_password('testpass123'))
    
    def test_admin_user_property(self):
        admin = User.objects.create_user(
            email='admin@example.com',
            username='admin',
            password='admin123',
            role=User.Role.ADMIN,
        )
        
        self.assertTrue(admin.is_admin_user)
        self.assertFalse(admin.is_sales_person_user)
    
    def test_sales_person_user_property(self):
        sales_user = User.objects.create_user(
            email='sales@example.com',
            username='sales',
            password='sales123',
            role=User.Role.SALES_PERSON,
        )
        
        self.assertFalse(sales_user.is_admin_user)
        self.assertTrue(sales_user.is_sales_person_user)

    def test_user_logo_field_defaults_to_empty(self):
        user = User.objects.create_user(
            email='logo@example.com',
            username='logouser',
            password='logopass123',
        )
        self.assertFalse(bool(user.logo))

    def test_user_logo_can_be_set(self):
        import io, tempfile
        from django.test import override_settings
        from django.core.files.images import ImageFile
        from PIL import Image

        user = User.objects.create_user(
            email='logo2@example.com',
            username='logo2user',
            password='logopass123',
        )

        with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            # Build a tiny in-memory PNG image.
            buf = io.BytesIO()
            Image.new('RGBA', (10, 10), color=(0, 91, 172, 255)).save(buf, format='PNG')
            buf.seek(0)
            user.logo.save('logo.png', ImageFile(buf), save=True)

            user.refresh_from_db()
            self.assertTrue(user.logo)
            self.assertTrue(user.logo.url.startswith('/media/'))
            self.assertIn('logos/', user.logo.name)


@pytest.mark.django_db
class TestNotificationModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='notif@example.com',
            username='notifuser',
            password='notifpass123',
        )
        self.customer = Customer.objects.create(
            company_name='Alert Test LLC',
            trade_license_number='998877',
        )
        expiring = date.today() + timedelta(days=10)
        self.notification = Notification.objects.create(
            user=self.user,
            type=Notification.Type.EXPIRY_7_DAYS,
            title='Trade License Expiring Soon: Alert Test LLC',
            message='The trade license for Alert Test LLC expires in 10 days.',
            customer=self.customer,
            document_type='trade_license',
            expiry_date=expiring,
        )

    def test_mark_as_read_updates_status_and_stamps_read_at(self):
        """mark_as_read() must not crash and must set read_at (timezone import)."""
        self.notification.mark_as_read()
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, Notification.Status.READ)
        self.assertIsNotNone(self.notification.read_at)

    def test_mark_as_read_is_idempotent(self):
        self.notification.mark_as_read()
        first_read_at = self.notification.read_at
        self.notification.mark_as_read()
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.read_at, first_read_at)

    def test_dismiss_sets_status(self):
        self.notification.dismiss()
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, Notification.Status.DISMISSED)
