"""
Views for audit app.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView

from .models import AuditLog


class AuditLogAccessMixin(UserPassesTestMixin):
    """Mixin to check audit log access permissions."""
    
    def test_func(self):
        return self.request.user.is_admin_user
    
    def handle_no_permission(self):
        messages.error(self.request, _('Only administrators can view audit logs.'))
        return redirect('customers:list')


class AuditLogListView(LoginRequiredMixin, AuditLogAccessMixin, ListView):
    model = AuditLog
    template_name = 'audit/list.html'
    context_object_name = 'logs'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = AuditLog.objects.select_related('user', 'customer').all()
        
        # Filters
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        customer_id = self.request.GET.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search) |
                Q(customer__company_name__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_choices'] = AuditLog.Action.choices
        context['current_action'] = self.request.GET.get('action', '')
        context['current_user'] = self.request.GET.get('user', '')
        context['current_customer'] = self.request.GET.get('customer', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['search'] = self.request.GET.get('search', '')
        return context


class AuditLogDetailView(LoginRequiredMixin, AuditLogAccessMixin, DetailView):
    model = AuditLog
    template_name = 'audit/detail.html'
    context_object_name = 'log'
    
    def get_queryset(self):
        return AuditLog.objects.select_related('user', 'customer')