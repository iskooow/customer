"""
Audit log utilities.
"""

from django.utils import timezone
from .models import AuditLog


def log_action(user, action, customer, description, request=None, object_type='', object_id=None, changes=None):
    """
    Log an action to the audit log.
    
    Args:
        user: User who performed the action
        action: Action type (from AuditLog.Action)
        customer: Customer instance (optional)
        description: Human-readable description
        request: HttpRequest object (optional)
        object_type: Type of object affected (optional)
        object_id: ID of object affected (optional)
        changes: Dictionary of changes made (optional)
    """
    ip_address = None
    user_agent = ''
    
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    AuditLog.objects.create(
        user=user,
        action=action,
        customer=customer,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        object_type=object_type,
        object_id=object_id,
        changes=changes or {},
    )


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')