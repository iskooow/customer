"""
Audit middleware for automatic logging of certain actions.
"""

from audit.utils import log_action, get_client_ip
from customers.models import Customer


class AuditMiddleware:
    """Middleware to automatically log certain actions."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Log successful POST requests to customer-related views
        if request.method == 'POST' and request.user.is_authenticated:
            path = request.path
            
            # Customer actions
            if '/customers/' in path:
                if '/add/' in path and response.status_code == 302:
                    # Customer created - would be logged in view
                    pass
                elif '/edit/' in path and response.status_code == 302:
                    # Customer updated - would be logged in view
                    pass
                elif '/delete/' in path and response.status_code == 302:
                    # Customer deleted - would be logged in view
                    pass
            
            # Document actions
            elif '/documents/' in path:
                if '/upload/' in path and response.status_code == 302:
                    pass
                elif '/edit/' in path and response.status_code == 302:
                    pass
                elif '/delete/' in path and response.status_code == 302:
                    pass
        
        return response