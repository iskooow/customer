"""
Efficient dashboard data computation for the KB Remicon Customer Record dashboard.

All statistics are derived from the live database using Django ORM aggregation
(Count / Q / annotate). No values are hard-coded.
"""

from django.db.models import Count, Q
from django.utils import timezone

from customers.models import Customer
from documents.models import Document
from salespersons.models import SalesPerson
from audit.models import AuditLog


# Colours (hex) used by the dashboard charts — aligned with the brand palette.
DONUT_COLORS = {
    'valid': '#22c55e',     # green
    'expiring': '#f59e0b',  # orange
    'expired': '#ef4444',   # red
    'missing': '#9ca3af',   # gray
}

DOCUMENT_TYPE_LABELS = {
    'trade_license': 'Trade License',
    'passport': 'Passport',
    'emirates_id': 'EID',
    'trn_certificate': 'TRN Certificate',
    'security_cheque': 'Security Cheque',
    'other': 'Other',
}


def _scoped_customers(user):
    """Return the Customer queryset scoped to the user's role."""
    customers = Customer.objects.all()
    if not user.is_admin_user:
        if hasattr(user, 'sales_person') and user.sales_person:
            customers = customers.filter(sales_person=user.sales_person)
        else:
            customers = customers.none()
    return customers


def _scoped_documents(customers_qs):
    """Documents attached to the given customer queryset."""
    return Document.objects.filter(customer__in=customers_qs)


def get_dashboard_data(user):
    """Compute all statistics needed by the main dashboard."""
    today = timezone.localdate()
    end_7 = today + timezone.timedelta(days=7)

    customers = _scoped_customers(user)
    documents = _scoped_documents(customers)
    customer_ids = list(customers.values_list('id', flat=True))

    # ---- Headline counts -------------------------------------------------
    total_customers = len(customer_ids)
    total_documents = documents.count()

    if user.is_admin_user:
        total_sales_persons = SalesPerson.objects.count()
    else:
        total_sales_persons = 1 if (
            hasattr(user, 'sales_person') and user.sales_person
        ) else 0

    # ---- Document expiry status (from the Document model) ----------------
    expired_documents = documents.filter(expiry_date__lt=today).count()
    expiring_7_days = documents.filter(
        expiry_date__gte=today, expiry_date__lte=end_7
    ).count()
    valid_documents = documents.filter(expiry_date__gt=end_7).count()

    # ---- Document-level status for the donut chart -------------------------
    # Documents without an expiry_date fall into a dedicated bucket so every
    # document appears in exactly one slice and the donut totals are correct.
    documents_without_expiry = documents.filter(expiry_date__isnull=True).count()

    # ---- Missing documents (customers missing at least one required doc) --
    # This is a customer-level metric used in KPI cards and alerts — NOT the
    # donut chart.  Kept separately so both views (per-document and per-
    # customer) are available to the template.
    missing_documents = customers.filter(
        ~Q(copy_status=Customer.CopyStatus.COMPLETE)
    ).count()

    # ---- Donut chart data --------------------------------------------------
    # All four slices are document counts; they sum to donut_total.
    donut_total = total_documents
    donut_data = [
        {
            'label': 'Valid Documents',
            'count': valid_documents,
            'color': DONUT_COLORS['valid'],
        },
        {
            'label': 'Expiring Soon',
            'count': expiring_7_days,
            'color': DONUT_COLORS['expiring'],
        },
        {
            'label': 'Expired',
            'count': expired_documents,
            'color': DONUT_COLORS['expired'],
        },
        {
            'label': 'No Expiry Set',
            'count': documents_without_expiry,
            'color': DONUT_COLORS['missing'],
        },
    ]
    for item in donut_data:
        item['percent'] = round(
            (item['count'] / donut_total * 100) if donut_total else 0,
            1,
        )

    # ---- Sales person summary & type counts & activity -------------------
    sales_person_summary = _build_sales_person_summary(customers, user)

    doc_types_qs = (
        documents
        .values('document_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    total_by_type = documents.count()
    document_type_counts = []
    for row in doc_types_qs:
        label = DOCUMENT_TYPE_LABELS.get(row['document_type'], row['document_type'])
        document_type_counts.append({
            'label': label,
            'count': row['count'],
            'percent': round(
                (row['count'] / total_by_type * 100) if total_by_type else 0, 1
            ),
        })

    recent_activity = list(
        AuditLog.objects
        .filter(
            Q(customer_id__in=customer_ids) | Q(customer_id__isnull=True)
        )
        .select_related('user', 'customer')
        .order_by('-timestamp')[:8]
    )

    return {
        'total_customers': total_customers,
        'total_sales_persons': total_sales_persons,
        'total_documents': total_documents,
        'expiring_7_days': expiring_7_days,
        'expired_documents': expired_documents,
        'valid_documents': valid_documents,
        'missing_documents': missing_documents,
        'donut_total': donut_total,
        'donut_data': donut_data,
        'sales_person_summary': sales_person_summary,
        'document_type_counts': document_type_counts,
        'recent_activity': recent_activity,
    }


def _build_sales_person_summary(customers, user):
    """Top 5 sales persons by customer count with document metrics."""
    today = timezone.localdate()
    end_7 = today + timezone.timedelta(days=7)

    if not user.is_admin_user:
        if hasattr(user, 'sales_person') and user.sales_person:
            return [
                {
                    'sales_person': user.sales_person,
                    'customer_count': customers.filter(
                        sales_person=user.sales_person
                    ).count(),
                    'document_count': 0,
                    'expiring_soon': 0,
                    'expired': 0,
                }
            ]
        return []

    # Customer counts per sales person
    cust_counts = dict(
        Customer.objects
        .values_list('sales_person_id')
        .annotate(total=Count('id'))
        .filter(sales_person_id__isnull=False)
        .order_by()
        .values_list('sales_person_id', 'total')
    )

    # Document totals per sales person
    doc_counts = dict(
        Document.objects
        .exclude(customer__sales_person_id__isnull=True)
        .values('customer__sales_person_id')
        .annotate(total=Count('id'))
        .values_list('customer__sales_person_id', 'total')
    )

    # Expiring (7 days) per sales person
    expiring_counts = dict(
        Document.objects
        .filter(expiry_date__gte=today, expiry_date__lte=end_7)
        .exclude(customer__sales_person_id__isnull=True)
        .values('customer__sales_person_id')
        .annotate(expiring=Count('id'))
        .values_list('customer__sales_person_id', 'expiring')
    )

    # Expired per sales person
    expired_counts = dict(
        Document.objects
        .filter(expiry_date__lt=today)
        .exclude(customer__sales_person_id__isnull=True)
        .values('customer__sales_person_id')
        .annotate(expired=Count('id'))
        .values_list('customer__sales_person_id', 'expired')
    )

    summary = []
    sales_persons = SalesPerson.objects.filter(id__in=cust_counts.keys())
    for sp in sales_persons:
        summary.append({
            'sales_person': sp,
            'customer_count': cust_counts.get(sp.id, 0),
            'document_count': doc_counts.get(sp.id, 0),
            'expiring_soon': expiring_counts.get(sp.id, 0),
            'expired': expired_counts.get(sp.id, 0),
        })

    summary.sort(key=lambda row: row['customer_count'], reverse=True)
    return summary[:5]

