# Customer Records & Document Expiry Management System

A professional Django-based customer records management application for UAE-based companies. Manage customer information, track document expiries, handle security cheques, and generate compliance reports.

## Features

### Core Functionality
- **Customer Management**: Complete CRUD operations for customer records
- **Document Expiry Tracking**: Automatic calculation of days remaining for Trade License, Passport, and Emirates ID
- **Expiry Status Indicators**: Visual badges (🟢 Valid, 🟡 Expiring Soon, 🟠 Urgent, 🔴 Expired)
- **Document Management**: Secure upload, view, download, and manage customer documents
- **Security Cheques**: Track cheque status (Received, Pending, Not Received, Returned)
- **Sales Person Management**: Assign customers to sales persons with role-based permissions
- **Dashboard**: Real-time statistics and alerts for expiring documents
- **Reports**: Generate PDF and Excel reports with filtering options
- **Excel Import/Export**: Bulk import customers from Excel with validation and preview
- **Audit Logging**: Track all important changes with user, action, and timestamp
- **Notifications**: In-app alerts for expiring documents and missing copies

### User Roles
- **Admin**: Full access to all features including user management, import/export, reports, and audit logs
- **Sales Person**: Access to assigned customers only, can add/edit customers, upload documents, view alerts

### Technical Stack
- **Backend**: Django 5.x, Django REST Framework
- **Database**: PostgreSQL (production), SQLite (development/testing)
- **Frontend**: Django Templates, Tailwind CSS, HTMX, Alpine.js
- **File Storage**: Local filesystem (development), S3-compatible (production)
- **Excel Processing**: openpyxl
- **PDF Generation**: ReportLab
- **Testing**: pytest, pytest-django

## Requirements

- Python 3.12+
- PostgreSQL 14+ (production)
- Node.js 18+ (for Tailwind CSS build if customizing)

## Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd customer_records
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Settings (PostgreSQL for production)
DB_NAME=customer_records
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Email Settings (optional - for notifications)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Customer Records <noreply@example.com>

# File Upload Settings
MAX_UPLOAD_SIZE=10485760
ALLOWED_EXTENSIONS=.pdf,.doc,.docx,.jpg,.jpeg,.png,.xlsx,.xls
```

### 5. Database Setup

For development (SQLite):
```bash
python manage.py migrate
```

For production (PostgreSQL):
1. Create database and user in PostgreSQL
2. Configure `.env` with PostgreSQL credentials
3. Run migrations:
```bash
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Seed Demo Data (Optional)

```bash
python manage.py seed_demo_data
```

This creates:
- 1 admin user (admin@example.com / admin123)
- 5 sales persons with user accounts (sales123 password)
- 20 demo customers with various expiry scenarios
- Security cheques and documents

### 8. Run Development Server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`

## Usage

### Login Credentials (After Seeding)
- **Admin**: admin@example.com / admin123
- **Sales Persons**: 
  - ahmed_mansouri@company.ae / sales123
  - fatima_zahra@company.ae / sales123
  - mohammed_rashidi@company.ae / sales123
  - aisha_qasimi@company.ae / sales123
  - khalid_nuaimi@company.ae / sales123

### Main Workflows

#### Adding a Customer
1. Navigate to **Customers** → **Add Customer**
2. Fill in Company Information, Passport, Emirates ID, Security Cheque sections
3. Upload document copies
4. Click **Save Customer** or **Save & Add Another**

#### Managing Documents
1. Open a customer detail page
2. Click **Upload Document** in the Documents section
3. Select document type, upload file, set expiry date
4. Documents are automatically linked to customer

#### Checking Expiries
- Dashboard shows summary cards for expiring documents
- **Expiry Alerts** page lists all expiring documents with filters
- Color-coded badges indicate urgency

#### Generating Reports
1. Go to **Reports** → Select report type
2. Apply filters (date range, sales person, document status, etc.)
3. Click **Export Excel** or **Export PDF**
4. For individual customer reports, use the **PDF** button on customer detail page

#### Excel Import
1. Navigate to **Customers** → **Import**
2. Download sample template or prepare Excel with required columns
3. Upload file → System validates and shows preview
4. Review errors/duplicates → Click **Import Valid Records**

### Excel Import Template Columns
```
S.N | COMPANY NAME | TRADE LICENSE | EXPIRE DATE | PASSPORT | PASSPORT EXPIRY | EID | EID EXPIRY | COPY | TRN | SECURITY CHEQUE | SALES PERSON
```

### Date Formats Accepted
- YYYY-MM-DD (2026-12-31)
- DD/MM/YYYY (31/12/2026)
- DD-MM-YYYY (31-12-2026)

## Management Commands

```bash
# Seed demo data
python manage.py seed_demo_data [--customers 20] [--salespersons 5] [--clear]

# Check expiries and create notifications
python manage.py check_expiries [--days 60 30 7 0] [--send-email] [--dry-run]

# Run tests
pytest

# Run specific tests
pytest tests/test_models.py -v
pytest tests/test_views.py -v
pytest tests/test_utils.py -v
```

## Production Deployment

### 1. Environment Variables
Set `DEBUG=False` and configure all production settings in `.env`:

```env
DEBUG=False
SECRET_KEY=your-very-long-random-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### 2. Static Files
```bash
python manage.py collectstatic --noinput
```

### 3. Database
Use PostgreSQL with connection pooling (PgBouncer recommended).

### 4. File Storage
Configure S3-compatible storage:
```python
# settings/production.py
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = 'your-bucket'
AWS_S3_REGION_NAME = 'your-region'
```

### 5. Web Server
Use Gunicorn with Nginx reverse proxy:

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

### 6. SSL/HTTPS
Configure SSL certificates (Let's Encrypt recommended) and set `SECURE_SSL_REDIRECT=True`.

### 7. Monitoring
- Set up Sentry for error tracking
- Configure logging to file/external service
- Monitor disk space for media files

## Project Structure

```
customer_records/
├── config/                 # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/               # User authentication & profiles
├── customers/              # Customer management (core)
├── documents/              # Document upload & management
├── salespersons/           # Sales person management
├── security_cheques/       # Security cheque tracking
├── reports/                # PDF/Excel report generation
├── audit/                  # Audit logging
├── notifications/          # Expiry alerts & notifications
├── templates/              # Django templates
├── static/                 # Static assets (CSS, JS)
├── media/                  # Uploaded files (gitignored)
├── tests/                  # Test suite
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Security Features

- Django's built-in CSRF protection
- Role-based permissions (not just UI hiding)
- Secure file uploads with type/size validation
- Document access requires authentication & authorization
- Password hashing with PBKDF2
- SQL injection protection via ORM
- XSS protection via template auto-escaping
- Secure session cookies in production

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=customers --cov=accounts --cov=documents --cov=salespersons --cov=security_cheques --cov=reports

# Run specific test module
pytest tests/test_models.py -v
pytest tests/test_views.py -v
pytest tests/test_utils.py -v
```

## License

This project is proprietary software for internal use.

## Support

For issues and feature requests, contact the development team.

---

**Built with Django for UAE Business Compliance**