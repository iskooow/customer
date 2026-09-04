"""
Views for salespersons app.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView

from .models import SalesPerson
from .forms import SalesPersonForm
from customers.models import Customer
from audit.utils import log_action


class SalesPersonAccessMixin(UserPassesTestMixin):
    """Mixin to check sales person access permissions."""
    
    def test_func(self):
        return self.request.user.is_admin_user
    
    def handle_no_permission(self):
        messages.error(self.request, _('Only administrators can manage sales persons.'))
        return redirect('salespersons:list')


class SalesPersonListView(LoginRequiredMixin, SalesPersonAccessMixin, ListView):
    model = SalesPerson
    template_name = 'salespersons/list.html'
    context_object_name = 'salespersons'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = SalesPerson.objects.annotate(
            customer_count=Count('customers')
        ).order_by('name')

        # Filter by search query
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(email__icontains=search)
            )

        # Filter by active status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(active=True)
        elif status == 'inactive':
            queryset = queryset.filter(active=False)

        return queryset

    def get_template_names(self):
        if getattr(self.request, 'htmx', False):
            return ['salespersons/partials/table.html']
        return ['salespersons/list.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add statistics for each sales person
        for sp in context['salespersons']:
            sp.expired_docs = sp.get_expired_documents_count()
            sp.expiring_soon = sp.get_expiring_soon_count(30)
            sp.missing_docs = sp.get_missing_documents_count()
            sp.pending_cheques = sp.get_pending_cheques_count()

        # Preserve the active search query in the template
        context['search'] = self.request.GET.get('search', '')

        return context


class SalesPersonDetailView(LoginRequiredMixin, DetailView):
    model = SalesPerson
    template_name = 'salespersons/detail.html'
    context_object_name = 'salesperson'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        salesperson = self.object
        
        # Get assigned customers with stats
        customers = salesperson.customers.select_related('sales_person').prefetch_related(
            'documents', 'security_cheques'
        )
        
        context['customers'] = customers
        context['total_customers'] = customers.count()
        context['active_customers'] = customers.filter(customer_status='active').count()
        context['expired_docs'] = salesperson.get_expired_documents_count()
        context['expiring_soon'] = salesperson.get_expiring_soon_count(30)
        context['missing_docs'] = salesperson.get_missing_documents_count()
        context['pending_cheques'] = salesperson.get_pending_cheques_count()
        
        return context


class SalesPersonCreateView(LoginRequiredMixin, SalesPersonAccessMixin, CreateView):
    model = SalesPerson
    form_class = SalesPersonForm
    template_name = 'salespersons/form.html'
    success_url = reverse_lazy('salespersons:list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            user=self.request.user,
            action='salesperson_created',
            customer=None,
            description=f'Created sales person: {self.object.name}',
            request=self.request,
        )
        messages.success(self.request, _('Sales person created successfully.'))
        return response


class SalesPersonUpdateView(LoginRequiredMixin, SalesPersonAccessMixin, UpdateView):
    model = SalesPerson
    form_class = SalesPersonForm
    template_name = 'salespersons/form.html'
    
    def get_success_url(self):
        return reverse('salespersons:detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            user=self.request.user,
            action='salesperson_updated',
            customer=None,
            description=f'Updated sales person: {self.object.name}',
            request=self.request,
        )
        messages.success(self.request, _('Sales person updated successfully.'))
        return response


class SalesPersonDeleteView(LoginRequiredMixin, SalesPersonAccessMixin, DeleteView):
    model = SalesPerson
    template_name = 'salespersons/confirm_delete.html'
    success_url = reverse_lazy('salespersons:list')
    
    def delete(self, request, *args, **kwargs):
        salesperson = self.get_object()
        
        # Check if sales person has customers
        if salesperson.customers.exists():
            messages.error(request, _('Cannot delete sales person with assigned customers. Reassign customers first.'))
            return redirect('salespersons:detail', pk=salesperson.pk)
        
        name = salesperson.name
        log_action(
            user=request.user,
            action='salesperson_deleted',
            customer=None,
            description=f'Deleted sales person: {name}',
            request=request,
        )
        messages.success(request, _('Sales person deleted successfully.'))
        return super().delete(request, *args, **kwargs)


class SalesPersonToggleActiveView(LoginRequiredMixin, SalesPersonAccessMixin, View):
    """Toggle sales person active status."""
    
    def post(self, request, pk):
        salesperson = get_object_or_404(SalesPerson, pk=pk)
        salesperson.active = not salesperson.active
        salesperson.save(update_fields=['active', 'updated_at'])
        
        action = 'activated' if salesperson.active else 'deactivated'
        log_action(
            user=request.user,
            action=f'salesperson_{action}',
            customer=None,
            description=f'{action.capitalize()} sales person: {salesperson.name}',
            request=request,
        )
        messages.success(request, _('Sales person {} successfully.').format(action))
        return redirect('salespersons:detail', pk=salesperson.pk)


class SalesPersonCustomerAssignView(LoginRequiredMixin, SalesPersonAccessMixin, View):
    """Assign customers to sales person."""
    
    def post(self, request, pk):
        salesperson = get_object_or_404(SalesPerson, pk=pk)
        customer_ids = request.POST.getlist('customer_ids')
        
        if customer_ids:
            customers = Customer.objects.filter(id__in=customer_ids)
            count = customers.update(sales_person=salesperson)
            
            for customer in customers:
                log_action(
                    user=request.user,
                    action='customer_reassigned',
                    customer=customer,
                    description=f'Reassigned to sales person: {salesperson.name}',
                    request=request,
                )
            
            messages.success(request, _('{} customers assigned to {}.').format(count, salesperson.name))
        else:
            messages.error(request, _('No customers selected.'))
        
        return redirect('salespersons:detail', pk=salesperson.pk)