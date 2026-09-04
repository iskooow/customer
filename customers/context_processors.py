"""
Context processors for the application.
"""

from django.templatetags.static import static

from customers.models import Customer
from security_cheques.models import SecurityCheque
from customers.dashboard import get_dashboard_data

FALLBACK_LOGO_URL = static('images/logo.svg')


def company_logo_url(request):
    """
    Make the current user's company logo (or a fallback) available in every
    template as ``{{ company_logo_url }}``.
    """
    user = getattr(request, 'user', None)
    if user and user.is_authenticated and getattr(user, 'logo', None):
        return {'company_logo_url': user.logo.url}
    return {'company_logo_url': FALLBACK_LOGO_URL}


def dashboard_stats(request):
    """
    Add dashboard statistics to all templates for authenticated users.
    """
    if not request.user.is_authenticated:
        return {}

    data = get_dashboard_data(request.user)

    # Customers scoped to the user's role (for status / pending-cheque counts)
    if request.user.is_admin_user:
        customers = Customer.objects.all()
        cheques = SecurityCheque.objects.all()
    else:
        if hasattr(request.user, 'sales_person') and request.user.sales_person:
            customers = Customer.objects.filter(sales_person=request.user.sales_person)
            cheques = SecurityCheque.objects.filter(
                customer__sales_person=request.user.sales_person
            )
        else:
            customers = Customer.objects.none()
            cheques = SecurityCheque.objects.none()

    return {
        'dashboard_stats': {
            'total_customers': data['total_customers'],
            'total_sales_persons': data['total_sales_persons'],
            'total_documents': data['total_documents'],
            'active_customers': customers.filter(customer_status='active').count(),
            'expired_documents': data['expired_documents'],
            'expiring_7_days': data['expiring_7_days'],
            'missing_documents': data['missing_documents'],
            'valid_documents': data['valid_documents'],
            'pending_cheques': cheques.filter(
                status__in=['pending', 'not_received']
            ).count(),
            # Real, per-user unread alert count so the navigation badge and the
            # Expiry Alerts inbox always agree.
            'unread_alerts': _unread_alerts_count(request.user),

        }
    }


def _unread_alerts_count(user):
    """Number of live (unread) notifications for the given user."""
    from notifications.models import Notification
    return Notification.objects.filter(
        user=user,
        status=Notification.Status.UNREAD,
    ).count()

