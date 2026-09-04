"""
Management command to seed demo data.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from customers.models import Customer
from salespersons.models import SalesPerson
from documents.models import Document
from security_cheques.models import SecurityCheque


class Command(BaseCommand):
    help = 'Seed database with demo data for testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--customers',
            type=int,
            default=20,
            help='Number of customers to create (default: 20)'
        )
        parser.add_argument(
            '--salespersons',
            type=int,
            default=5,
            help='Number of salespersons to create (default: 5)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding'
        )
    
    def handle(self, *args, **options):
        num_customers = options['customers']
        num_salespersons = options['salespersons']
        clear = options['clear']
        
        if clear:
            self.stdout.write('Clearing existing data...')
            SecurityCheque.objects.all().delete()
            Document.objects.all().delete()
            Customer.objects.all().delete()
            SalesPerson.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
        
        # Create admin user if not exists
        admin_user, created = User.objects.get_or_create(
            email='admin@example.com',
            defaults={
                'username': 'admin',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Created admin user: admin@example.com / admin123'))
        
        # Create sales persons
        salesperson_names = [
            ('Ahmed Al Mansouri', 'ahmed.mansouri@company.ae', '+971 50 123 4567'),
            ('Fatima Al Zahra', 'fatima.zahra@company.ae', '+971 50 234 5678'),
            ('Mohammed Al Rashidi', 'mohammed.rashidi@company.ae', '+971 50 345 6789'),
            ('Aisha Al Qasimi', 'aisha.qasimi@company.ae', '+971 50 456 7890'),
            ('Khalid Al Nuaimi', 'khalid.nuaimi@company.ae', '+971 50 567 8901'),
            ('Sarah Johnson', 'sarah.johnson@company.ae', '+971 50 678 9012'),
            ('David Smith', 'david.smith@company.ae', '+971 50 789 0123'),
            ('Emily Brown', 'emily.brown@company.ae', '+971 50 890 1234'),
        ]
        
        salespersons = []
        for i, (name, email, phone) in enumerate(salesperson_names[:num_salespersons]):
            sp, created = SalesPerson.objects.get_or_create(
                email=email,
                defaults={
                    'name': name,
                    'phone': phone,
                    'active': True,
                }
            )
            if created:
                # Create user account for sales person
                username = email.split('@')[0].replace('.', '_')
                user = User.objects.create(
                    username=username,
                    email=email,
                    first_name=name.split()[0],
                    last_name=' '.join(name.split()[1:]),
                    role=User.Role.SALES_PERSON,
                    phone=phone,
                    sales_person=sp,
                    is_active=True,
                )
                user.set_password('sales123')
                user.save()
            salespersons.append(sp)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(salespersons)} sales persons'))
        
        # UAE-style company names
        company_templates = [
            ('{name} {suffix} LLC', ['Al', 'Emirates', 'Gulf', 'Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Umm Al Quwain', 'Ras Al Khaimah', 'Fujairah']),
            ('{name} {industry} {suffix}', ['Al', 'Emirates', 'Gulf', 'Dubai', 'Abu Dhabi']),
            ('{name} {industry} {suffix} LLC', ['Al', 'Emirates', 'Gulf']),
            ('{name} Group {suffix}', ['Al', 'Emirates', 'Gulf', 'Dubai']),
            ('{name} Trading {suffix}', ['Al', 'Emirates', 'Gulf']),
            ('{name} Contracting {suffix}', ['Al', 'Emirates', 'Gulf']),
            ('{name} Engineering {suffix}', ['Al', 'Emirates', 'Gulf']),
            ('{name} Construction {suffix}', ['Al', 'Emirates', 'Gulf']),
        ]
        
        industries = [
            'Ready Mix', 'Construction', 'Trading', 'Engineering', 'Contracting',
            'Building Materials', 'Logistics', 'Transport', 'Marine', 'Oil & Gas',
            'Electrical', 'Mechanical', 'Civil', 'Interior', 'Landscaping',
            'Steel', 'Aluminum', 'Glass', 'Plumbing', 'HVAC'
        ]
        
        suffixes = ['LLC', 'Ltd', 'Group', 'Est', 'Corp']
        
        # Generate unique company names
        used_names = set()
        companies = []
        
        while len(companies) < num_customers:
            template, prefixes = random.choice(company_templates)
            prefix = random.choice(prefixes)
            industry = random.choice(industries)
            suffix = random.choice(suffixes)
            
            name = template.format(
                name=prefix,
                industry=industry,
                suffix=suffix
            )
            
            if name not in used_names:
                used_names.add(name)
                companies.append(name)
        
        # Create customers with various expiry scenarios
        today = date.today()
        
        # Status distribution
        status_weights = [
            (Customer.CustomerStatus.ACTIVE, 0.8),
            (Customer.CustomerStatus.INACTIVE, 0.15),
            (Customer.CustomerStatus.PENDING, 0.05),
        ]
        
        copy_status_weights = [
            (Customer.CopyStatus.COMPLETE, 0.4),
            (Customer.CopyStatus.PARTIAL, 0.35),
            (Customer.CopyStatus.MISSING, 0.25),
        ]
        
        cheque_status_weights = [
            (SecurityCheque.Status.RECEIVED, 0.4),
            (SecurityCheque.Status.PENDING, 0.25),
            (SecurityCheque.Status.NOT_RECEIVED, 0.25),
            (SecurityCheque.Status.RETURNED, 0.1),
        ]
        
        for i, company_name in enumerate(companies):
            # Random sales person
            sales_person = random.choice(salespersons)
            
            # Customer status
            customer_status = random.choices(
                [s[0] for s in status_weights],
                weights=[s[1] for s in status_weights]
            )[0]
            
            # Generate dates for different scenarios
            # Trade license expiry
            tl_scenario = random.choices(
                ['valid', 'expired', 'expiring_7', 'expiring_30', 'expiring_60'],
                weights=[0.4, 0.15, 0.1, 0.2, 0.15]
            )[0]
            
            if tl_scenario == 'valid':
                tl_expiry = today + timedelta(days=random.randint(61, 365))
            elif tl_scenario == 'expired':
                tl_expiry = today - timedelta(days=random.randint(1, 90))
            elif tl_scenario == 'expiring_7':
                tl_expiry = today + timedelta(days=random.randint(1, 7))
            elif tl_scenario == 'expiring_30':
                tl_expiry = today + timedelta(days=random.randint(8, 30))
            else:  # expiring_60
                tl_expiry = today + timedelta(days=random.randint(31, 60))
            
            # Passport expiry
            pp_scenario = random.choices(
                ['valid', 'expired', 'expiring_7', 'expiring_30', 'expiring_60'],
                weights=[0.45, 0.1, 0.1, 0.2, 0.15]
            )[0]
            
            if pp_scenario == 'valid':
                pp_expiry = today + timedelta(days=random.randint(61, 1825))  # up to 5 years
            elif pp_scenario == 'expired':
                pp_expiry = today - timedelta(days=random.randint(1, 180))
            elif pp_scenario == 'expiring_7':
                pp_expiry = today + timedelta(days=random.randint(1, 7))
            elif pp_scenario == 'expiring_30':
                pp_expiry = today + timedelta(days=random.randint(8, 30))
            else:
                pp_expiry = today + timedelta(days=random.randint(31, 60))
            
            # EID expiry
            eid_scenario = random.choices(
                ['valid', 'expired', 'expiring_7', 'expiring_30', 'expiring_60'],
                weights=[0.5, 0.05, 0.1, 0.2, 0.15]
            )[0]
            
            if eid_scenario == 'valid':
                eid_expiry = today + timedelta(days=random.randint(61, 1825))
            elif eid_scenario == 'expired':
                eid_expiry = today - timedelta(days=random.randint(1, 90))
            elif eid_scenario == 'expiring_7':
                eid_expiry = today + timedelta(days=random.randint(1, 7))
            elif eid_scenario == 'expiring_30':
                eid_expiry = today + timedelta(days=random.randint(8, 30))
            else:
                eid_expiry = today + timedelta(days=random.randint(31, 60))
            
            # Generate random document numbers
            tl_number = f'{random.randint(100000, 999999)}'
            pp_number = f'{random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}{random.randint(1000000, 9999999)}'
            eid_number = f'784-{random.randint(1900, 2025)}-{random.randint(1000000, 9999999)}-{random.randint(1, 9)}'
            trn = f'100{random.randint(10000000000, 99999999999)}'
            
            customer = Customer.objects.create(
                company_name=company_name,
                trade_license_number=tl_number,
                trade_license_expiry=tl_expiry,
                trn=trn,
                sales_person=sales_person,
                customer_status=customer_status,
                passport_number=pp_number,
                passport_expiry=pp_expiry,
                eid_number=eid_number,
                eid_expiry=eid_expiry,
                created_by=admin_user,
                updated_by=admin_user,
            )
            
            # Create security cheque
            cheque_status = random.choices(
                [s[0] for s in cheque_status_weights],
                weights=[s[1] for s in cheque_status_weights]
            )[0]
            
            cheque = SecurityCheque.objects.create(
                customer=customer,
                status=cheque_status,
                cheque_number=f'CHQ{random.randint(100000, 999999)}',
                amount=Decimal(random.randint(10000, 500000)) / 100 if random.random() > 0.3 else None,
                cheque_date=today - timedelta(days=random.randint(1, 180)) if random.random() > 0.3 else None,
                created_by=admin_user,
                updated_by=admin_user,
            )
            
            # Create documents based on copy status
            copy_status = random.choices(
                [s[0] for s in copy_status_weights],
                weights=[s[1] for s in copy_status_weights]
            )[0]
            
            # Always create at least some documents
            doc_types_to_create = []
            
            if copy_status == Customer.CopyStatus.COMPLETE:
                doc_types_to_create = ['trade_license', 'passport', 'emirates_id', 'trn_certificate']
            elif copy_status == Customer.CopyStatus.PARTIAL:
                doc_types_to_create = random.sample(['trade_license', 'passport', 'emirates_id', 'trn_certificate'], k=random.randint(1, 3))
            else:  # MISSING
                if random.random() < 0.3:  # 30% chance of having at least one doc
                    doc_types_to_create = [random.choice(['trade_license', 'passport', 'emirates_id', 'trn_certificate'])]
            
            # Add optional documents
            if random.random() < 0.3:
                doc_types_to_create.append('security_cheque')
            
            for doc_type in doc_types_to_create:
                if doc_type == 'trade_license':
                    expiry = tl_expiry
                elif doc_type == 'passport':
                    expiry = pp_expiry
                elif doc_type == 'emirates_id':
                    expiry = eid_expiry
                elif doc_type == 'security_cheque':
                    expiry = cheque.cheque_date
                else:
                    expiry = None
                
                Document.objects.create(
                    customer=customer,
                    document_type=doc_type,
                    file_name=f'{doc_type}_{company_name[:20].replace(" ", "_")}.pdf',
                    file_size=random.randint(100000, 5000000),
                    expiry_date=expiry,
                    uploaded_by=admin_user,
                )
            
            # Update copy status
            customer.update_copy_status()
            
            if (i + 1) % 10 == 0:
                self.stdout.write(f'Created {i + 1} customers...')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {num_customers} demo customers'))
        self.stdout.write(self.style.SUCCESS('Demo data seeding complete!'))
        self.stdout.write('Login credentials:')
        self.stdout.write('  Admin: admin@example.com / admin123')
        self.stdout.write('  Sales: ahmed_mansouri@company.ae / sales123 (and similar for others)')