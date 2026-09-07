"""
Tests for the shared dashboard statistics (customers.dashboard.get_dashboard_data).

Covers the document-status donut chart, in particular that TRN Certificate
documents — which never expire — are counted as "Valid Documents" rather than
being excluded from the chart entirely.
"""

from datetime import date, timedelta

import pytest
from django.test import TestCase

from accounts.models import User
from customers.models import Customer
from customers.dashboard import get_dashboard_data
from documents.models import Document
from salespersons.models import SalesPerson


@pytest.mark.django_db
class GetDashboardDataTests(TestCase):
    """Unit tests for customers.dashboard.get_dashboard_data."""

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
            name='Jane Doe',
            email='jane@example.com',
            phone='+971 50 123 4567',
        )

        self.customer = Customer.objects.create(
            company_name='Acme LLC',
            trade_license_number='TL123',
            trn='100123456789003',
            sales_person=self.sales_person,
            created_by=self.admin,
            updated_by=self.admin,
        )

    def _add_document(self, document_type, expiry_date=None):
        """Create a Document row on the shared test customer."""
        return Document.objects.create(
            customer=self.customer,
            document_type=document_type,
            expiry_date=expiry_date,
            file_name='doc.pdf',
            file_size=1000,
            uploaded_by=self.admin,
        )

    def test_trn_certificate_counts_as_valid_document(self):
        """Regression: TRN Certificate (no expiry) must appear as a valid doc.

        Previously only documents with an ``expiry_date`` were included in
        the donut chart, so a permanent TRN Certificate was silently dropped
        from ``valid_documents`` and the donut total.
        """
        today = date.today()
        self._add_document(Document.DocumentType.TRN_CERTIFICATE)          # valid (no expiry)
        self._add_document(
            Document.DocumentType.TRADE_LICENSE,
            expiry_date=today + timedelta(days=30),                        # valid
        )
        self._add_document(
            Document.DocumentType.PASSPORT,
            expiry_date=today + timedelta(days=3),                         # expiring soon
        )
        self._add_document(
            Document.DocumentType.EMIRATES_ID,
            expiry_date=today - timedelta(days=5),                         # expired
        )

        data = get_dashboard_data(self.admin)

        self.assertEqual(data['valid_documents'], 2)       # TRN + trade license
        self.assertEqual(data['expiring_7_days'], 1)
        self.assertEqual(data['expired_documents'], 1)
        self.assertEqual(data['donut_total'], 4)

        donut = {item['label']: item['count'] for item in data['donut_data']}
        self.assertEqual(donut['Valid Documents'], 2)
        self.assertEqual(donut['Expiring Soon'], 1)
        self.assertEqual(donut['Expired'], 1)

    def test_documents_without_expiry_are_not_donut_documents(self):
        """Security Cheque / Other (no expiry) stay out of the donut.

        Only TRN Certificate is treated as permanently valid; other
        undated document types are not part of expiry monitoring and still
        must not inflate the chart.
        """
        today = date.today()
        self._add_document(Document.DocumentType.SECURITY_CHEQUE)
        self._add_document(Document.DocumentType.OTHER)
        self._add_document(
            Document.DocumentType.TRADE_LICENSE,
            expiry_date=today + timedelta(days=30),
        )

        data = get_dashboard_data(self.admin)

        # 1 valid, 0 expiring, 0 expired — the two undated docs are excluded.
        self.assertEqual(data['total_documents'], 3)
        self.assertEqual(data['valid_documents'], 1)
        self.assertEqual(data['expiring_7_days'], 0)
        self.assertEqual(data['expired_documents'], 0)
        self.assertEqual(data['donut_total'], 1)

    def test_trn_document_with_expiry_date_still_counts_as_valid(self):
        """Even if a TRN expiry date is set, it is never expiring/expired."""
        today = date.today()
        # Edge case: someone uploaded a TRN with a date in the past.
        self._add_document(
            Document.DocumentType.TRN_CERTIFICATE,
            expiry_date=today - timedelta(days=10),
        )

        data = get_dashboard_data(self.admin)

        self.assertEqual(data['valid_documents'], 1)
        self.assertEqual(data['expired_documents'], 0)
        self.assertEqual(data['donut_total'], 1)