"""
Views for security_cheques app.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, DetailView, View
from django.db.models import Q
from django.http import FileResponse
import os

from .models import SecurityCheque
from .forms import SecurityChequeForm
from customers.models import Customer
from audit.utils import log_action


class ChequeAccessMixin(UserPassesTestMixin):
    """Mixin to check security cheque access permissions."""
    
    def test_func(self):
        cheque = get_object_or_404(SecurityCheque, pk=self.kwargs['pk'])
        user = self.request.user
        
        if user.is_admin_user:
            return True
        
        if user.is_sales_person_user and hasattr(user, 'sales_person'):
            return cheque.customer.sales_person == user.sales_person
        
        return False


class SecurityChequeCreateView(LoginRequiredMixin, CreateView):
    model = SecurityCheque
    form_class = SecurityChequeForm
    template_name = 'security_cheques/form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['customer'] = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
        return context
    
    def form_valid(self, form):
        customer = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
        
        # Check permissions
        if not self.request.user.is_admin_user:
            if not (self.request.user.is_sales_person_user and 
                    hasattr(self.request.user, 'sales_person') and 
                    customer.sales_person == self.request.user.sales_person):
                messages.error(self.request, _('You do not have permission to add cheques for this customer.'))
                return redirect('customers:detail', pk=customer.pk)
        
        form.instance.customer = customer
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        
        log_action(
            user=self.request.user,
            action='cheque_created',
            customer=customer,
            description=f'Added security cheque: {self.object.get_status_display()}',
            request=self.request,
        )
        messages.success(self.request, _('Security cheque added successfully.'))
        return response
    
    def get_success_url(self):
        return reverse('customers:detail', kwargs={'pk': self.object.customer.pk})


class SecurityChequeUpdateView(LoginRequiredMixin, ChequeAccessMixin, UpdateView):
    model = SecurityCheque
    form_class = SecurityChequeForm
    template_name = 'security_cheques/form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.object.customer
        return context
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        log_action(
            user=self.request.user,
            action='cheque_updated',
            customer=self.object.customer,
            description=f'Updated security cheque: {self.object.get_status_display()}',
            request=self.request,
        )
        messages.success(self.request, _('Security cheque updated successfully.'))
        return response
    
    def get_success_url(self):
        return reverse('customers:detail', kwargs={'pk': self.object.customer.pk})


class SecurityChequeDeleteView(LoginRequiredMixin, ChequeAccessMixin, DeleteView):
    model = SecurityCheque
    template_name = 'security_cheques/confirm_delete.html'
    context_object_name = 'cheque'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin_user:
            messages.error(request, _('Only administrators can delete security cheques.'))
            return redirect('customers:detail', pk=self.get_object().customer.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        cheque = self.get_object()
        customer = cheque.customer
        log_action(
            user=request.user,
            action='cheque_deleted',
            customer=customer,
            description=f'Deleted security cheque: {cheque.get_status_display()}',
            request=request,
        )
        messages.success(request, _('Security cheque deleted successfully.'))
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('customers:detail', kwargs={'pk': self.object.customer.pk})


class SecurityChequeListView(LoginRequiredMixin, ListView):
    model = SecurityCheque
    template_name = 'security_cheques/list.html'
    context_object_name = 'cheques'
    paginate_by = 25

    def get_template_names(self):
        """Render only the table partial for HTMX requests."""
        if getattr(self.request, 'htmx', None):
            return ['security_cheques/partials/table.html']
        return ['security_cheques/list.html']

    def get_queryset(self):
        queryset = SecurityCheque.objects.select_related('customer', 'customer__sales_person', 'created_by')
        
        # Apply user-based filtering
        if not self.request.user.is_admin_user:
            if hasattr(self.request.user, 'sales_person') and self.request.user.sales_person:
                queryset = queryset.filter(customer__sales_person=self.request.user.sales_person)
            else:
                queryset = queryset.none()
        
        # Filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(customer__company_name__icontains=search) | Q(cheque_number__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = SecurityCheque.Status.choices
        context['current_status'] = self.request.GET.get('status', '')
        context['search'] = self.request.GET.get('search', '')
        return context


class SecurityChequeDownloadView(LoginRequiredMixin, ChequeAccessMixin, View):
    """Secure cheque copy download."""
    
    def get(self, request, pk):
        cheque = get_object_or_404(SecurityCheque, pk=pk)
        
        if not cheque.file or not os.path.exists(cheque.file.path):
            messages.error(request, _('File not found.'))
            return redirect('customers:detail', pk=cheque.customer.pk)
        
        log_action(
            user=request.user,
            action='cheque_downloaded',
            customer=cheque.customer,
            description=f'Downloaded security cheque copy',
            request=request,
        )
        
        return FileResponse(
            open(cheque.file.path, 'rb'),
            as_attachment=True,
            filename=cheque.file_name or f'cheque_{cheque.id}.pdf'
        )


class SecurityChequeBulkUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Bulk update security cheque statuses."""
    
    def test_func(self):
        return self.request.user.is_admin_user
    
    def post(self, request):
        cheque_ids = request.POST.getlist('cheque_ids')
        new_status = request.POST.get('status')
        
        if not cheque_ids or not new_status:
            messages.error(request, _('Invalid request.'))
            return redirect('security_cheques:list')
        
        if new_status not in dict(SecurityCheque.Status.choices):
            messages.error(request, _('Invalid status.'))
            return redirect('security_cheques:list')
        
        cheques = SecurityCheque.objects.filter(id__in=cheque_ids)
        count = cheques.update(status=new_status, updated_by=request.user)
        
        for cheque in cheques:
            log_action(
                user=request.user,
                action='cheque_bulk_updated',
                customer=cheque.customer,
                description=f'Bulk updated security cheque status to {new_status}',
                request=request,
            )
        
        messages.success(request, _('Updated {} security cheques to {}.').format(count, new_status))
        return redirect('security_cheques:list')