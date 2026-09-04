"""
Views for documents app.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, Http404, FileResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView, View
from django.conf import settings
import os

from .models import Document
from .forms import DocumentForm
from customers.models import Customer
from audit.utils import log_action


class DocumentAccessMixin(UserPassesTestMixin):
    """Mixin to check document access permissions."""
    
    def test_func(self):
        document = get_object_or_404(Document, pk=self.kwargs['pk'])
        user = self.request.user
        
        if user.is_admin_user:
            return True
        
        if user.is_sales_person_user and hasattr(user, 'sales_person'):
            return document.customer.sales_person == user.sales_person
        
        return False


class DocumentUploadView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = 'documents/upload.html'
    
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
                messages.error(self.request, _('You do not have permission to upload documents for this customer.'))
                return redirect('customers:detail', pk=customer.pk)
        
        form.instance.customer = customer
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        
        log_action(
            user=self.request.user,
            action='document_uploaded',
            customer=customer,
            description=f'Uploaded {self.object.get_document_type_display()}: {self.object.file_name}',
            request=self.request,
        )
        messages.success(self.request, _('Document uploaded successfully.'))
        return response
    
    def get_success_url(self):
        return reverse('customers:detail', kwargs={'pk': self.object.customer.pk})


class DocumentUpdateView(LoginRequiredMixin, DocumentAccessMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = 'documents/edit.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(
            user=self.request.user,
            action='document_updated',
            customer=self.object.customer,
            description=f'Updated {self.object.get_document_type_display()}: {self.object.file_name}',
            request=self.request,
        )
        messages.success(self.request, _('Document updated successfully.'))
        return response
    
    def get_success_url(self):
        return reverse('customers:detail', kwargs={'pk': self.object.customer.pk})


class DocumentDeleteView(LoginRequiredMixin, DocumentAccessMixin, DeleteView):
    model = Document
    template_name = 'documents/confirm_delete.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin_user:
            messages.error(request, _('Only administrators can delete documents.'))
            return redirect('customers:detail', pk=self.get_object().customer.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        document = self.get_object()
        customer = document.customer
        file_name = document.file_name
        doc_type = document.get_document_type_display()
        
        log_action(
            user=request.user,
            action='document_deleted',
            customer=customer,
            description=f'Deleted {doc_type}: {file_name}',
            request=request,
        )
        messages.success(request, _('Document deleted successfully.'))
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('customers:detail', kwargs={'pk': self.object.customer.pk})


class DocumentDownloadView(LoginRequiredMixin, DocumentAccessMixin, View):
    """Secure document download view."""
    
    def get(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        
        # Check if file exists
        if not document.file or not os.path.exists(document.file.path):
            messages.error(request, _('File not found.'))
            return redirect('customers:detail', pk=document.customer.pk)
        
        # Log access
        log_action(
            user=request.user,
            action='document_downloaded',
            customer=document.customer,
            description=f'Downloaded {document.get_document_type_display()}: {document.file_name}',
            request=request,
        )
        
        # Serve file
        response = FileResponse(
            open(document.file.path, 'rb'),
            as_attachment=True,
            filename=document.file_name
        )
        return response


class DocumentViewView(LoginRequiredMixin, DocumentAccessMixin, View):
    """View document inline (for PDFs and images)."""
    
    def get(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        
        if not document.file or not os.path.exists(document.file.path):
            messages.error(request, _('File not found.'))
            return redirect('customers:detail', pk=document.customer.pk)
        
        # Log access
        log_action(
            user=request.user,
            action='document_viewed',
            customer=document.customer,
            description=f'Viewed {document.get_document_type_display()}: {document.file_name}',
            request=request,
        )
        
        # Serve file inline
        response = FileResponse(
            open(document.file.path, 'rb'),
            as_attachment=False,
        )
        return response


class DocumentListView(LoginRequiredMixin, View):
    """List all documents with filtering."""
    
    ALLOWED_SORTS = [
        'file_name', '-file_name',
        'customer__company_name', '-customer__company_name',
        'document_type', '-document_type',
        'expiry_date', '-expiry_date',
        'uploaded_by__username', '-uploaded_by__username',
        'uploaded_at', '-uploaded_at',
    ]
    
    def get(self, request):
        from django.db.models import Q
        from django.core.paginator import Paginator
        
        documents = Document.objects.select_related('customer', 'uploaded_by').all()
        
        # Apply user-based filtering
        if not request.user.is_admin_user:
            if hasattr(request.user, 'sales_person') and request.user.sales_person:
                documents = documents.filter(customer__sales_person=request.user.sales_person)
            else:
                documents = documents.none()
        
        # Filters
        doc_type = request.GET.get('type')
        if doc_type:
            documents = documents.filter(document_type=doc_type)
        
        customer_id = request.GET.get('customer')
        if customer_id:
            documents = documents.filter(customer_id=customer_id)
        
        search = request.GET.get('search')
        if search:
            documents = documents.filter(
                Q(file_name__icontains=search) |
                Q(customer__company_name__icontains=search) |
                Q(notes__icontains=search)
            )
        
        # Sorting
        sort = request.GET.get('sort', '-uploaded_at')
        if sort in self.ALLOWED_SORTS:
            documents = documents.order_by(sort)
        else:
            documents = documents.order_by('-uploaded_at')
        
        # Pagination
        paginator = Paginator(documents, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'documents/list.html', {
            'page_obj': page_obj,
            'doc_types': Document.DocumentType.choices,
            'current_type': doc_type,
            'search': search,
            'sort': sort,
        })