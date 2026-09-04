"""
Shared logic for generating expiry/compliance notifications.

The daily refresh (management command) and the on-demand "Refresh alerts"
view both call :func:`run_expiry_scan` so the in-app alerts always reflect
the current state of the customer/documents tables regardless of how the
scan is triggered.
"""

from datetime import date

from django.utils import timezone

from accounts.models import User
from customers.models import Customer
from notifications.models import Notification, NotificationPreference

# (customer field, document_type, label) for the document types we track.
DOCUMENTS = [
    ('trade_license_expiry', 'trade_license', 'Trade License'),
    ('passport_expiry', 'passport', 'Passport'),
    ('eid_expiry', 'emirates_id', 'Emirates ID'),
]

# Required documents the customer's ``copy_status`` (and the missing-document
# alerts) are evaluated against.  Kept in sync with
# ``Customer.update_copy_status``.  TRN Certificate is required but has no
# customer-level expiry field, so it lives here and NOT in ``DOCUMENTS``.
REQUIRED_DOCUMENTS = {
    'trade_license': 'Trade License',
    'passport': 'Passport',
    'emirates_id': 'Emirates ID',
    'trn_certificate': 'TRN Certificate',
}


def run_expiry_scan(user_scope=None, send_email=False, dry_run=False):
    """
    Evaluate customers/documents against expiry windows and (re)create
    in-app notifications, returning a small result summary.

    ``user_scope`` narrows the scan to a specific user's relevant customers
    (used by the UI "refresh" action). When ``None`` every customer is
    scanned (used by the management command / admins).

    Returns: dict with created_count, skipped_count, dismissed_count.
    """
    customers = Customer.objects.select_related(
        'sales_person', 'sales_person__user_account'
    ).all()

    if user_scope is not None and not user_scope.is_admin_user:
        if getattr(user_scope, 'sales_person', None):
            customers = customers.filter(sales_person=user_scope.sales_person)
        else:
            customers = customers.none()

    created = skipped = dismissed = 0

    # --- Document expiry windows ----------------------------------------
    for customer in customers:
        recipients = _get_recipients(customer, user_scope=user_scope)

        for field_name, doc_type, label in DOCUMENTS:
            expiry_date = getattr(customer, field_name)
            if not expiry_date:
                continue

            alert = _classify_expiry(expiry_date)
            if alert is None:
                # Fine / far from expiry: drop any stale live alert for it.
                dismissed += _dismiss_previous(
                    customer, doc_type, recipients
                )
                continue

            notif_type, title, message = _build_alert(
                customer, label, expiry_date, alert
            )
            for user in recipients:
                if not _in_app_enabled(user, notif_type):
                    skipped += 1
                    continue
                if _exists_today(customer, doc_type, notif_type, user):
                    skipped += 1
                    continue
                if not dry_run:
                    Notification.objects.create(
                        user=user,
                        type=notif_type,
                        title=title,
                        message=message,
                        customer=customer,
                        document_type=doc_type,
                        expiry_date=expiry_date,
                    )
                created += 1

    # --- Missing documents (customers with partial/missing copies) -------
    missing_customers = customers.filter(
        copy_status__in=[Customer.CopyStatus.PARTIAL, Customer.CopyStatus.MISSING]
    )
    for customer in missing_customers:
        recipients = _get_recipients(customer, user_scope=user_scope)
        missing_docs = _missing_document_labels(customer)
        if not missing_docs:
            continue
        for user in recipients:
            if not _in_app_enabled(user, Notification.Type.MISSING_DOCUMENTS):
                skipped += 1
                continue
            if _exists_today(customer, None, Notification.Type.MISSING_DOCUMENTS, user):
                skipped += 1
                continue
            if not dry_run:
                Notification.objects.create(
                    user=user,
                    type=Notification.Type.MISSING_DOCUMENTS,
                    title=f'Missing Documents: {customer.company_name}',
                    message=(
                        f'{customer.company_name} is missing required documents: '
                        f'{", ".join(missing_docs)}.'
                    ),
                    customer=customer,
                )
            created += 1

    # --- Pending security cheques -----------------------------------------
    cheque_customers = customers.filter(
        security_cheques__status__in=['pending', 'not_received']
    ).distinct()
    for customer in cheque_customers:
        recipients = _get_recipients(customer, user_scope=user_scope)
        for user in recipients:
            if not _in_app_enabled(user, Notification.Type.CHEQUE_PENDING):
                skipped += 1
                continue
            if _exists_today(customer, None, Notification.Type.CHEQUE_PENDING, user):
                skipped += 1
                continue
            if not dry_run:
                pending_cheques = customer.security_cheques.filter(
                    status__in=['pending', 'not_received']
                )
                Notification.objects.create(
                    user=user,
                    type=Notification.Type.CHEQUE_PENDING,
                    title=f'Pending Security Cheques: {customer.company_name}',
                    message=(
                        f'{customer.company_name} has {pending_cheques.count()} '
                        f'pending security cheque(s).'
                    ),
                    customer=customer,
                )
            created += 1

    return {
        'created_count': created,
        'skipped_count': skipped,
        'dismissed_count': dismissed,
    }




def _get_recipients(customer, user_scope=None):
    """Assigned sales person (if any) plus active admins, deduped.

    When ``user_scope`` is an admin we still fan out to all admins (they can
    see everything). A sales-person scope restricts to just that user.
    """
    recipients = []
    if customer.sales_person:
        user_account = getattr(customer.sales_person, 'user_account', None)
        if user_account:
            recipients.append(user_account)
    recipients.extend(User.objects.filter(role=User.Role.ADMIN, is_active=True))

    if user_scope is not None and not user_scope.is_admin_user:
        # Sales person triggers a refresh for themselves only.
        recipients = [u for u in recipients if u.pk == user_scope.pk]

    return list(set(recipients))


def _classify_expiry(expiry_date):
    """Return the alert key for a date, or None if no alert is needed."""
    days_left = (expiry_date - date.today()).days
    if days_left < 0:
        return 'expired'
    if days_left == 0:
        return 'today'
    if days_left <= 7:
        return '7_days'
    if days_left <= 30:
        return '30_days'
    if days_left <= 60:
        return '60_days'
    return None


def _build_alert(customer, label, expiry_date, alert):
    display_date = expiry_date.strftime('%d %b %Y')
    days_left = (expiry_date - date.today()).days
    company = customer.company_name

    if alert == 'expired':
        notif_type = Notification.Type.EXPIRED
        title = f'{label} Expired: {company}'
        message = (
            f'The {label.lower()} for {company} expired on '
            f'{display_date} ({abs(days_left)} days ago).'
        )
    elif alert == 'today':
        notif_type = Notification.Type.EXPIRY_7_DAYS
        title = f'{label} Expires Today: {company}'
        message = (
            f'The {label.lower()} for {company} expires today ({display_date}). '
            'It needs immediate attention.'
        )
    elif alert == '7_days':
        notif_type = Notification.Type.EXPIRY_7_DAYS
        title = f'{label} Expiring Soon: {company}'
        message = (
            f'The {label.lower()} for {company} expires in '
            f'{days_left} days ({display_date}).'
        )
    elif alert == '30_days':
        notif_type = Notification.Type.EXPIRY_30_DAYS
        title = f'{label} Expiring in 30 Days: {company}'
        message = (
            f'The {label.lower()} for {company} expires in '
            f'{days_left} days ({display_date}).'
        )
    else:  # 60_days
        notif_type = Notification.Type.EXPIRY_60_DAYS
        title = f'{label} Expiring in 60 Days: {company}'
        message = (
            f'The {label.lower()} for {company} expires in '
            f'{days_left} days ({display_date}).'
        )
    return notif_type, title, message


def _missing_document_labels(customer):
    """Human-readable labels for the required documents a customer lacks."""
    uploaded = set(customer.documents.values_list('document_type', flat=True))
    return [
        label for doc_type, label in REQUIRED_DOCUMENTS.items()
        if doc_type not in uploaded
    ]


def _exists_today(customer, doc_type, notif_type, user):
    qs = Notification.objects.filter(
        user=user,
        customer=customer,
        type=notif_type,
        status__in=[Notification.Status.UNREAD, Notification.Status.READ],
        created_at__date=timezone.localdate(),
    )
    if doc_type is not None:
        qs = qs.filter(document_type=doc_type)
    return qs.exists()


def _dismiss_previous(customer, doc_type, recipients):
    dismissed = 0
    for user in recipients:
        matching = Notification.objects.filter(
            user=user,
            customer=customer,
            document_type=doc_type,
            status__in=[Notification.Status.UNREAD, Notification.Status.READ],
        )
        if matching.exists():
            dismissed += matching.count()
            matching.update(status=Notification.Status.DISMISSED)
    return dismissed


def _in_app_enabled(user, notif_type):
    """Whether the user has enabled in-app alerts for ``notif_type``."""
    pref_map = {
        Notification.Type.EXPIRY_60_DAYS: 'in_app_expiry_60_days',
        Notification.Type.EXPIRY_30_DAYS: 'in_app_expiry_30_days',
        Notification.Type.EXPIRY_7_DAYS: 'in_app_expiry_7_days',
        Notification.Type.EXPIRED: 'in_app_expired',
        Notification.Type.MISSING_DOCUMENTS: 'in_app_missing_documents',
        Notification.Type.CHEQUE_PENDING: 'in_app_cheque_pending',
    }
    field = pref_map.get(notif_type)
    if not field:
        return True
    try:
        prefs = user.notification_preferences
    except NotificationPreference.DoesNotExist:
        # No preferences row -> defaults apply (all enabled).
        return True
    return bool(getattr(prefs, field, True))

