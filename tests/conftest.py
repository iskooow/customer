"""
Pytest configuration and fixtures.
"""

import pytest
from django.conf import settings


def pytest_configure(config):
    """Configure Django settings for pytest."""
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            SECRET_KEY='test-secret-key-for-testing-only',
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.admin',
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.messages',
                'django.contrib.staticfiles',
                'rest_framework',
                'django_filters',
                'crispy_forms',
                'crispy_tailwind',
                'django_tables2',
                'django_htmx',
                'widget_tweaks',
                'accounts',
                'customers',
                'documents',
                'salespersons',
                'security_cheques',
                'reports',
                'audit',
                'notifications',
            ],
            MIDDLEWARE=[
                'django.middleware.security.SecurityMiddleware',
                'django.contrib.sessions.middleware.SessionMiddleware',
                'django.middleware.common.CommonMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
                'django.middleware.clickjacking.XFrameOptionsMiddleware',
                'django_htmx.middleware.HtmxMiddleware',
            ],
            ROOT_URLCONF='config.urls',
            TEMPLATES=[{
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [],
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.debug',
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                        'customers.context_processors.company_logo_url',
                    ],
                    'loaders': [
                        'django.template.loaders.filesystem.Loader',
                        'django.template.loaders.app_directories.Loader',
                    ],
                },
            }],
            AUTH_PASSWORD_VALIDATORS=[],
            AUTH_USER_MODEL='accounts.User',
            LANGUAGE_CODE='en-us',
            TIME_ZONE='Asia/Dubai',
            USE_I18N=True,
            USE_TZ=True,
            STATIC_URL='/static/',
            MEDIA_URL='/media/',
            DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
            REST_FRAMEWORK={
                'DEFAULT_FILTER_BACKENDS': [
                    'django_filters.rest_framework.DjangoFilterBackend',
                ],
                'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
                'PAGE_SIZE': 25,
            },
            CRISPY_ALLOWED_TEMPLATE_PACKS='tailwind',
            CRISPY_TEMPLATE_PACK='tailwind',
            DJANGO_TABLES2_TEMPLATE='django_tables2/tailwind.html',
            PASSWORD_HASHERS=[
                'django.contrib.auth.hashers.MD5PasswordHasher',
            ],
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    from accounts.models import User
    return User.objects.create_user(
        email='admin@example.com',
        username='admin',
        password='admin123',
        first_name='Admin',
        last_name='User',
        role=User.Role.ADMIN,
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def sales_user(db):
    """Create a sales person user."""
    from accounts.models import User
    from salespersons.models import SalesPerson
    
    sp = SalesPerson.objects.create(
        name='John Doe',
        email='john@example.com',
        phone='+971 50 123 4567',
    )
    
    user = User.objects.create_user(
        email='sales@example.com',
        username='sales',
        password='sales123',
        first_name='John',
        last_name='Doe',
        role=User.Role.SALES_PERSON,
        phone='+971 50 123 4567',
        sales_person=sp,
    )
    return user


@pytest.fixture
def sales_person(db):
    """Create a sales person."""
    from salespersons.models import SalesPerson
    return SalesPerson.objects.create(
        name='John Doe',
        email='john@example.com',
        phone='+971 50 123 4567',
    )


@pytest.fixture
def customer(db, admin_user, sales_person):
    """Create a test customer."""
    from customers.models import Customer
    from datetime import date, timedelta
    
    return Customer.objects.create(
        company_name='Test Company LLC',
        trade_license_number='123456',
        trade_license_expiry=date.today() + timedelta(days=30),
        trn='100123456789003',
        sales_person=sales_person,
        created_by=admin_user,
        updated_by=admin_user,
    )