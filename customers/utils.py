"""
Utility functions for customer expiry calculations.
"""

from datetime import date, timedelta
from django.utils.translation import gettext_lazy as _


def get_days_left(expiry_date):
    """
    Calculate days left until expiry date.
    
    Args:
        expiry_date: A date object
        
    Returns:
        int: Days left (negative if expired), or None if no date
    """
    if not expiry_date:
        return None
    
    today = date.today()
    delta = expiry_date - today
    return delta.days


def get_expiry_status(expiry_date):
    """
    Get expiry status based on days left.
    
    Args:
        expiry_date: A date object
        
    Returns:
        dict: Contains 'status', 'label', 'css_class', 'icon'
    """
    days_left = get_days_left(expiry_date)
    
    if days_left is None:
        return {
            'status': 'unknown',
            'label': _('Not Set'),
            'css_class': 'bg-gray-100 text-gray-600',
            'icon': '❓',
        }
    
    if days_left < 0:
        return {
            'status': 'expired',
            'label': _('EXPIRED'),
            'css_class': 'bg-red-100 text-red-700',
            'icon': '🔴',
        }
    elif days_left == 0:
        return {
            'status': 'expires_today',
            'label': _('EXPIRES TODAY'),
            'css_class': 'bg-red-100 text-red-700',
            'icon': '🔴',
        }
    elif days_left <= 7:
        return {
            'status': 'urgent',
            'label': _('URGENT'),
            'css_class': 'bg-orange-100 text-orange-700',
            'icon': '🟠',
        }
    elif days_left <= 30:
        return {
            'status': 'expiring_soon',
            'label': _('EXPIRING SOON'),
            'css_class': 'bg-yellow-100 text-yellow-700',
            'icon': '🟡',
        }
    elif days_left <= 60:
        return {
            'status': 'expiring_soon',
            'label': _('EXPIRING SOON'),
            'css_class': 'bg-yellow-100 text-yellow-700',
            'icon': '🟡',
        }
    else:
        return {
            'status': 'valid',
            'label': _('VALID'),
            'css_class': 'bg-green-100 text-green-700',
            'icon': '🟢',
        }


def get_copy_status_label(copy_status):
    """Get display label for copy status."""
    labels = {
        'complete': _('Complete'),
        'partial': _('Partial'),
        'missing': _('Missing'),
    }
    return labels.get(copy_status, copy_status)


def get_copy_status_icon(copy_status):
    """Get icon for copy status."""
    icons = {
        'complete': '✓',
        'partial': '⚠',
        'missing': '✕',
    }
    return icons.get(copy_status, '✕')


def get_copy_status_css(copy_status):
    """Get CSS class for copy status."""
    classes = {
        'complete': 'bg-green-100 text-green-700',
        'partial': 'bg-yellow-100 text-yellow-700',
        'missing': 'bg-red-100 text-red-700',
    }
    return classes.get(copy_status, 'bg-gray-100 text-gray-700')


def format_days_left(days):
    """Format days left for display."""
    if days is None:
        return _('Not Set')
    if days < 0:
        return _('EXPIRED')
    return str(days)


def get_expiry_filter_queryset(queryset, filter_type, field_name):
    """
    Filter queryset by expiry status.
    
    Args:
        queryset: Base queryset
        filter_type: One of 'expired', '7_days', '30_days', '60_days', 'valid'
        field_name: The date field to filter on
        
    Returns:
        Filtered queryset
    """
    from django.db.models import Q
    from datetime import date, timedelta
    
    today = date.today()
    
    if filter_type == 'expired':
        return queryset.filter(**{f'{field_name}__lt': today})
    elif filter_type == '7_days':
        return queryset.filter(**{f'{field_name}__gte': today, f'{field_name}__lte': today + timedelta(days=7)})
    elif filter_type == '30_days':
        return queryset.filter(**{f'{field_name}__gte': today, f'{field_name}__lte': today + timedelta(days=30)})
    elif filter_type == '60_days':
        return queryset.filter(**{f'{field_name}__gte': today, f'{field_name}__lte': today + timedelta(days=60)})
    elif filter_type == 'valid':
        return queryset.filter(**{f'{field_name}__gt': today + timedelta(days=60)})
    
    return queryset