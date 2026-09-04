"""Reproduce the security cheque upload against config.settings (production) with rollback."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import transaction
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from accounts.models import User
from security_cheques.models import SecurityCheque
from django.urls import reverse

# Pick an admin user and a customer
admin = User.objects.filter(is_superuser=True).first()
print('ADMIN', admin)
if not admin:
    print('NO ADMIN FOUND - abort')
    raise SystemExit

from customers.models import Customer
customer = Customer.objects.order_by('id').first()
print('CUSTOMER', customer and customer.pk, customer and customer.company_name)
if not customer:
    print('NO CUSTOMER - abort')
    raise SystemExit

try:
    with transaction.atomic():
        client = Client()
        client.force_login(admin)
        upload = SimpleUploadedFile('prod_cheque.pdf', b'%PDF-1.4 content', content_type='application/pdf')
        data = {
            'status': 'received',
            'cheque_number': 'CHQ-PROD-REPRO',
            'amount': '999.00',
            'cheque_date': '2026-08-31',
            'file': upload,
        }
        resp = client.post(reverse('security_cheques:add', kwargs={'customer_pk': customer.pk}), data, HTTP_HOST='localhost')
        print('POST STATUS', resp.status_code)
        qs = SecurityCheque.objects.filter(cheque_number='CHQ-PROD-REPRO')
        print('RECORD EXISTS', qs.exists())
        for c in qs:
            print('  PK', c.pk, 'CUST', c.customer_id, 'STATUS', c.status,
                  'FILE', repr(str(c.file)), 'FILE_NAME', repr(c.file_name),
                  'CREATED', c.created_at)
        # List view
        resp2 = client.get(reverse('security_cheques:list'), HTTP_HOST='localhost')
        print('LIST STATUS', resp2.status_code)
        print('LIST CONTAINS', 'CHQ-PROD-REPRO' in resp2.content.decode())
        # Explicitly raise to roll back
        raise RuntimeError('rollback')
except RuntimeError:
    pass
print('ROLLED BACK')
