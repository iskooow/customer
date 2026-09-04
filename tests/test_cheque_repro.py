"""Temporary reproduction for security cheque upload issue (removed after validation)."""
from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from customers.models import Customer
from salespersons.models import SalesPerson
from security_cheques.models import SecurityCheque


class SecurityChequeUploadRepro(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com', username='admin', password='admin123',
            first_name='Admin', last_name='User', role=User.Role.ADMIN,
            is_staff=True, is_superuser=True,
        )
        self.sp = SalesPerson.objects.create(name='Ali Mohammed', email='ali@example.com')
        self.customer = Customer.objects.create(
            company_name='KB Test LLC', sales_person=self.sp,
            created_by=self.admin, updated_by=self.admin,
        )

    def test_upload_file_creates_record(self):
        self.client.login(email='admin@example.com', password='admin123')
        upload = SimpleUploadedFile(
            'cheque.pdf',
            b'%PDF-1.4 test content',
            content_type='application/pdf',
        )
        data = {
            'status': 'received',
            'cheque_number': 'CHQ-UPLOAD-1',
            'amount': '2500.00',
            'cheque_date': date.today().strftime('%Y-%m-%d'),
            'file': upload,
        }
        resp = self.client.post(
            reverse('security_cheques:add', kwargs={'customer_pk': self.customer.pk}),
            data,
        )
        print('STATUS', resp.status_code)
        qs = SecurityCheque.objects.filter(cheque_number='CHQ-UPLOAD-1')
        print('RECORD_EXISTS', qs.exists())
        if qs.exists():
            c = qs.first()
            print('PK', c.pk)
            print('CUSTOMER_ID', c.customer_id)
            print('FILE_NAME', repr(c.file_name))
            print('FILE_FIELD', repr(str(c.file)))
            print('STATUS', c.status)
            print('CREATED', c.created_at)
        # List page should show it
        resp2 = self.client.get(reverse('security_cheques:list'))
        self.assertEqual(resp2.status_code, 200)
        print('LIST_CONTAINS', 'CHQ-UPLOAD-1' in resp2.content.decode())
        # Customer detail should show it
        resp3 = self.client.get(reverse('customers:detail', kwargs={'pk': self.customer.pk}))
        print('DETAIL_CONTAINS', 'CHQ-UPLOAD-1' in resp3.content.decode())
