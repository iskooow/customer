"""
Views for reports app.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Count
from django.http import HttpResponse, FileResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, View, FormView
from django.utils import timezone
from datetime import date, timedelta

from customers.models import Customer
from salespersons.models import SalesPerson
from security_cheques.models import SecurityCheque
from documents.models import Document
from .excel_reports import (
    generate_customer_excel_report,
    generate_expiring_documents_excel,
    generate_missing_documents_excel,
    generate_salesperson_excel,
    generate_security_cheque_excel,
)
from .pdf_reports import (
    generate_customer_pdf_report,
    generate_expiring_documents_pdf,
    generate_missing_documents_pdf,
    generate_salesperson_pdf,
    generate_security_cheque_pdf,
    generate_individual_customer_pdf,
)
from .forms import ReportFilterForm
from customers.dashboard import get_dashboard_data


class ReportAccessMixin(UserPassesTestMixin):
    """Mixin to check report access permissions."""
    
    def test_func(self):
        return self.request.user.is_admin_user or self.request.user.is_sales_person_user
    
    def handle_no_permission(self):
        messages.error(self.request, _('Only administrators and sales persons can access reports.'))
        return redirect('customers:list')


class ReportsDashboardView(LoginRequiredMixin, ReportAccessMixin, View):
    """Main KB Remicon dashboard with live KPIs, charts and summaries."""

    def get(self, request):
        data = get_dashboard_data(request.user)

        context = {
            'stats': data,
            'donut_data': data['donut_data'],
            'donut_total': data['donut_total'],
            'sales_person_summary': data['sales_person_summary'],
            'document_type_counts': data['document_type_counts'],
            'recent_activity': data['recent_activity'],
        }
        return render(request, 'reports/dashboard.html', context)


class ReportsIndexView(LoginRequiredMixin, ReportAccessMixin, View):
    """Reports landing page with report-type cards and advanced filters."""

    def get(self, request):
        form = ReportFilterForm(request.GET)
        return render(request, 'reports/index.html', {
            'form': form,
            'report_types': [
                ('customer', _('Customer Compliance Report')),
                ('expired', _('Expired Documents')),
                ('expiring', _('Expiring Documents')),
                ('missing', _('Missing Documents')),
                ('salesperson', _('Salesperson Report')),
                ('cheque', _('Security Cheque Report')),
            ],
        })



class CustomerReportView(LoginRequiredMixin, ReportAccessMixin, View):
    """Customer compliance report with filters."""
    
    def get_queryset(self, request):
        queryset = Customer.objects.select_related('sales_person').prefetch_related('documents', 'security_cheques')
        
        # Apply user-based filtering for sales persons
        if not request.user.is_admin_user:
            if hasattr(request.user, 'sales_person') and request.user.sales_person:
                queryset = queryset.filter(sales_person=request.user.sales_person)
            else:
                queryset = queryset.none()
        
        # Apply filters from GET params
        form = ReportFilterForm(request.GET)
        if form.is_valid():
            # Customer status
            customer_status = form.cleaned_data.get('customer_status')
            if customer_status:
                queryset = queryset.filter(customer_status=customer_status)
            
            # Sales person
            sales_person = form.cleaned_data.get('sales_person')
            if sales_person:
                queryset = queryset.filter(sales_person=sales_person)
            
            # Trade license filters
            tl_status = form.cleaned_data.get('trade_license_status')
            if tl_status:
                from customers.utils import get_expiry_filter_queryset
                queryset = get_expiry_filter_queryset(queryset, tl_status, 'trade_license_expiry')
            
            # Passport filters
            pp_status = form.cleaned_data.get('passport_status')
            if pp_status:
                from customers.utils import get_expiry_filter_queryset
                queryset = get_expiry_filter_queryset(queryset, pp_status, 'passport_expiry')
            
            # EID filters
            eid_status = form.cleaned_data.get('eid_status')
            if eid_status:
                from customers.utils import get_expiry_filter_queryset
                queryset = get_expiry_filter_queryset(queryset, eid_status, 'eid_expiry')
            
            # Copy status
            copy_status = form.cleaned_data.get('copy_status')
            if copy_status:
                queryset = queryset.filter(copy_status=copy_status)
            
            # Security cheque status
            cheque_status = form.cleaned_data.get('cheque_status')
            if cheque_status:
                queryset = queryset.filter(security_cheques__status=cheque_status).distinct()
            
            # Date range
            date_from = form.cleaned_data.get('date_from')
            date_to = form.cleaned_data.get('date_to')
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.distinct()
    
    def get(self, request):
        queryset = self.get_queryset(request)
        format_type = request.GET.get('format', 'html')
        
        if format_type == 'excel':
            return self.export_excel(request, queryset)
        elif format_type == 'pdf':
            return self.export_pdf(request, queryset)
        else:
            # HTML view
            return self.render_html(request, queryset)
    
    def render_html(self, request, queryset):
        from django.core.paginator import Paginator
        
        paginator = Paginator(queryset, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Add computed fields
        for customer in page_obj:
            customer.tl_days_left = customer.get_trade_license_days_left()
            customer.tl_status = customer.get_trade_license_status()
            customer.pp_days_left = customer.get_passport_days_left()
            customer.pp_status = customer.get_passport_status()
            customer.eid_days_left = customer.get_eid_days_left()
            customer.eid_status = customer.get_eid_status()
        
        return render(request, 'reports/customer_report.html', {
            'page_obj': page_obj,
            'total_count': queryset.count(),
        })
    
    def _get_selected_sales_person(self, request):
        """Resolve the selected SalesPerson from the GET filter, or None."""
        sp_id = request.GET.get('sales_person')
        if not sp_id:
            return None
        try:
            return SalesPerson.objects.get(pk=sp_id)
        except (SalesPerson.DoesNotExist, ValueError):
            return None

    def export_excel(self, request, queryset):
        filters = dict(request.GET)
        filters = {k: v[0] for k, v in filters.items() if v and v[0]}
        return generate_customer_excel_report(
            queryset,
            filters=filters,
            user=request.user,
            sales_person=self._get_selected_sales_person(request),
        )

    def export_pdf(self, request, queryset):
        filters = dict(request.GET)
        filters = {k: v[0] for k, v in filters.items() if v and v[0]}
        sales_person = self._get_selected_sales_person(request)
        buffer = generate_customer_pdf_report(queryset, filters=filters, sales_person=sales_person)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        if sales_person:
            from .excel_reports import _sanitize_filename_component
            safe_name = _sanitize_filename_component(sales_person.name)
            pdf_filename = f'KB_Remicon_Customer_Compliance_Report_{safe_name}.pdf'
        else:
            pdf_filename = f'KB_Remicon_Customer_Compliance_Report_{date.today()}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response


class ExpiredDocumentsReportView(LoginRequiredMixin, ReportAccessMixin, View):
    """Expired documents report."""
    
    def get(self, request):
        from customers.utils import get_expiry_filter_queryset
        
        queryset = Customer.objects.select_related('sales_person').prefetch_related('documents')
        
        if not request.user.is_admin_user:
            if hasattr(request.user, 'sales_person') and request.user.sales_person:
                queryset = queryset.filter(sales_person=request.user.sales_person)
            else:
                queryset = queryset.none()
        
        doc_type = request.GET.get('doc_type', 'all')
        format_type = request.GET.get('format', 'html')
        
        # Salesperson filter from GET param
        sales_person_id = request.GET.get('sales_person')
        selected_sales_person = None
        if sales_person_id:
            try:
                selected_sales_person = SalesPerson.objects.get(pk=sales_person_id)
                queryset = queryset.filter(sales_person=selected_sales_person)
            except (SalesPerson.DoesNotExist, ValueError):
                pass

        if doc_type == 'trade_license':
            queryset = get_expiry_filter_queryset(queryset, 'expired', 'trade_license_expiry')
            title = _('Expired Trade Licenses')
        elif doc_type == 'passport':
            queryset = get_expiry_filter_queryset(queryset, 'expired', 'passport_expiry')
            title = _('Expired Passports')
        elif doc_type == 'emirates_id':
            queryset = get_expiry_filter_queryset(queryset, 'expired', 'eid_expiry')
            title = _('Expired Emirates IDs')
        else:
            # All expired
            today = date.today()
            queryset = queryset.filter(
                Q(trade_license_expiry__lt=today) |
                Q(passport_expiry__lt=today) |
                Q(eid_expiry__lt=today)
            )
            title = _('All Expired Documents')
        
        if format_type == 'excel':
            return generate_expiring_documents_excel(queryset, doc_type, 0, title)
        elif format_type == 'pdf':
            buffer = generate_expiring_documents_pdf(queryset, doc_type, 0, title)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="expired_documents_{date.today()}.pdf"'
            return response
        
        # HTML view with pagination
        from django.core.paginator import Paginator
        paginator = Paginator(queryset, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        for customer in page_obj:
            customer.tl_days_left = customer.get_trade_license_days_left()
            customer.tl_status = customer.get_trade_license_status()
            customer.pp_days_left = customer.get_passport_days_left()
            customer.pp_status = customer.get_passport_status()
            customer.eid_days_left = customer.get_eid_days_left()
            customer.eid_status = customer.get_eid_status()
        
        return render(request, 'reports/expired_documents.html', {
            'page_obj': page_obj,
            'total_count': queryset.count(),
            'doc_type': doc_type,
            'title': title,
            'sales_persons': SalesPerson.objects.filter(active=True),
            'selected_sales_person': selected_sales_person,
            'sales_person_id': sales_person_id,
        })


class ExpiringDocumentsReportView(LoginRequiredMixin, ReportAccessMixin, View):
    """Expiring documents report."""
    
    def get(self, request):
        from customers.utils import get_expiry_filter_queryset
        
        queryset = Customer.objects.select_related('sales_person').prefetch_related('documents')
        
        if not request.user.is_admin_user:
            if hasattr(request.user, 'sales_person') and request.user.sales_person:
                queryset = queryset.filter(sales_person=request.user.sales_person)
            else:
                queryset = queryset.none()
        
        doc_type = request.GET.get('doc_type', 'all')

        # Salesperson filter from GET param
        sales_person_id = request.GET.get('sales_person')
        selected_sales_person = None
        if sales_person_id:
            try:
                selected_sales_person = SalesPerson.objects.get(pk=sales_person_id)
                queryset = queryset.filter(sales_person=selected_sales_person)
            except (SalesPerson.DoesNotExist, ValueError):
                pass


        days = int(request.GET.get('days', 30))
        format_type = request.GET.get('format', 'html')
        
        if doc_type == 'trade_license':
            queryset = get_expiry_filter_queryset(queryset, f'{days}_days', 'trade_license_expiry')
            title = _('Trade Licenses Expiring in {} Days').format(days)
        elif doc_type == 'passport':
            queryset = get_expiry_filter_queryset(queryset, f'{days}_days', 'passport_expiry')
            title = _('Passports Expiring in {} Days').format(days)
        elif doc_type == 'emirates_id':
            queryset = get_expiry_filter_queryset(queryset, f'{days}_days', 'eid_expiry')
            title = _('Emirates IDs Expiring in {} Days').format(days)
        else:
            # All documents expiring within days
            today = date.today()
            threshold = today + timedelta(days=days)
            queryset = queryset.filter(
                Q(trade_license_expiry__gte=today, trade_license_expiry__lte=threshold) |
                Q(passport_expiry__gte=today, passport_expiry__lte=threshold) |
                Q(eid_expiry__gte=today, eid_expiry__lte=threshold)
            )
            title = _('All Documents Expiring in {} Days').format(days)
        
        if format_type == 'excel':
            return generate_expiring_documents_excel(queryset, doc_type, days, title)
        elif format_type == 'pdf':
            buffer = generate_expiring_documents_pdf(queryset, doc_type, days, title)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="expiring_documents_{days}d_{date.today()}.pdf"'
            return response
        
        # HTML view
        from django.core.paginator import Paginator
        paginator = Paginator(queryset, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        for customer in page_obj:
            customer.tl_days_left = customer.get_trade_license_days_left()
            customer.tl_status = customer.get_trade_license_status()
            customer.pp_days_left = customer.get_passport_days_left()
            customer.pp_status = customer.get_passport_status()
            customer.eid_days_left = customer.get_eid_days_left()
            customer.eid_status = customer.get_eid_status()
        
        return render(request, 'reports/expiring_documents.html', {
            'page_obj': page_obj,
            'total_count': queryset.count(),
            'doc_type': doc_type,
            'days': days,
            'title': title,
            'sales_persons': SalesPerson.objects.filter(active=True),
            'selected_sales_person': selected_sales_person,
            'sales_person_id': sales_person_id,
        })


class MissingDocumentsReportView(LoginRequiredMixin, ReportAccessMixin, View):
    """Missing documents report."""
    
    def get(self, request):
        queryset = Customer.objects.select_related('sales_person').prefetch_related('documents').exclude(
            copy_status=Customer.CopyStatus.COMPLETE
        )
        
        if not request.user.is_admin_user:
            if hasattr(request.user, 'sales_person') and request.user.sales_person:
                queryset = queryset.filter(sales_person=request.user.sales_person)
            else:
                queryset = queryset.none()
        

        # Salesperson filter from GET param
        sales_person_id = request.GET.get('sales_person')
        selected_sales_person = None
        if sales_person_id:
            try:
                selected_sales_person = SalesPerson.objects.get(pk=sales_person_id)
                queryset = queryset.filter(sales_person=selected_sales_person)
            except (SalesPerson.DoesNotExist, ValueError):
                pass


        format_type = request.GET.get('format', 'html')
        
        if format_type == 'excel':
            return generate_missing_documents_excel(queryset)
        elif format_type == 'pdf':
            buffer = generate_missing_documents_pdf(queryset)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="missing_documents_{date.today()}.pdf"'
            return response
        
        # HTML view
        from django.core.paginator import Paginator
        paginator = Paginator(queryset, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'reports/missing_documents.html', {
            'page_obj': page_obj,
            'total_count': queryset.count(),
            'sales_persons': SalesPerson.objects.filter(active=True),
            'selected_sales_person': selected_sales_person,
            'sales_person_id': sales_person_id,
        })


class SalespersonReportView(LoginRequiredMixin, ReportAccessMixin, View):
    """Salesperson performance report.

    - Without ?salesperson_id: shows card overview of all salespersons.
    - With ?salesperson_id=N: shows customer compliance table for that person.
    """

    def get(self, request):
        from django.core.paginator import Paginator

        sales_person_id = request.GET.get('salesperson_id')
        selected_sales_person = None
        show_customer_table = False

        if sales_person_id:
            try:
                selected_sales_person = SalesPerson.objects.get(pk=sales_person_id)
                show_customer_table = True
            except (SalesPerson.DoesNotExist, ValueError):
                pass

        if show_customer_table:
            # -- Customer compliance table for the selected salesperson --
            queryset = Customer.objects.select_related(
                'sales_person'
            ).prefetch_related('documents', 'security_cheques').filter(
                sales_person=selected_sales_person
            )

            if not request.user.is_admin_user:
                if hasattr(request.user, 'sales_person') and request.user.sales_person:
                    queryset = queryset.filter(sales_person=request.user.sales_person)
                else:
                    queryset = queryset.none()

            format_type = request.GET.get('format', 'html')

            if format_type == 'excel':
                return generate_customer_excel_report(queryset)
            elif format_type == 'pdf':
                buffer = generate_customer_pdf_report(queryset)
                resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
                resp['Content-Disposition'] = (
                    f'attachment; filename="customer_report_{selected_sales_person.name}_{date.today()}.pdf"'
                )
                return resp

            paginator = Paginator(queryset, 50)
            page_obj = paginator.get_page(request.GET.get('page'))

            for customer in page_obj:
                customer.tl_days_left = customer.get_trade_license_days_left()
                customer.tl_status = customer.get_trade_license_status()
                customer.pp_days_left = customer.get_passport_days_left()
                customer.pp_status = customer.get_passport_status()
                customer.eid_days_left = customer.get_eid_days_left()
                customer.eid_status = customer.get_eid_status()

            return render(request, 'reports/salesperson_report.html', {
                'show_customer_table': True,
                'selected_sales_person': selected_sales_person,
                'salespersons': SalesPerson.objects.filter(active=True),
                'page_obj': page_obj,
                'total_count': queryset.count(),
            })

        # -- Card overview of all salespersons (default) --
        queryset = SalesPerson.objects.filter(active=True).annotate(
            customer_count=Count('customers')
        ).order_by('name')

        format_type = request.GET.get('format', 'html')

        if format_type == 'excel':
            return generate_salesperson_excel(queryset)
        elif format_type == 'pdf':
            buffer = generate_salesperson_pdf(queryset)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="salesperson_report_{date.today()}.pdf"'
            return response

        for sp in queryset:
            sp.expired_docs = sp.get_expired_documents_count()
            sp.expiring_soon = sp.get_expiring_soon_count(30)
            sp.missing_docs = sp.get_missing_documents_count()
            sp.pending_cheques = sp.get_pending_cheques_count()

        return render(request, 'reports/salesperson_report.html', {
            'show_customer_table': False,
            'salespersons': queryset,
        })

class SecurityChequeReportView(LoginRequiredMixin, ReportAccessMixin, View):
    """Security cheque report."""
    
    def get(self, request):
        queryset = SecurityCheque.objects.select_related('customer', 'customer__sales_person')
        
        if not request.user.is_admin_user:
            if hasattr(request.user, 'sales_person') and request.user.sales_person:
                queryset = queryset.filter(customer__sales_person=request.user.sales_person)
            else:
                queryset = queryset.none()
        
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        search = request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(customer__company_name__icontains=search) | Q(cheque_number__icontains=search)
            )

        format_type = request.GET.get('format', 'html')
        
        if format_type == 'excel':
            return generate_security_cheque_excel(queryset)
        elif format_type == 'pdf':
            buffer = generate_security_cheque_pdf(queryset)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="security_cheque_report_{date.today()}.pdf"'
            return response
        
        # HTML view
        from django.core.paginator import Paginator
        paginator = Paginator(queryset, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'total_count': queryset.count(),
            'status_choices': SecurityCheque.Status.choices,
            'current_status': status,
            'search': request.GET.get('search', ''),
        }

        if request.htmx:
            # Partial table response for HTMX swaps
            return render(request, 'reports/partials/cheque_table.html', context)
        return render(request, 'reports/security_cheque_report.html', context)


class IndividualCustomerReportView(LoginRequiredMixin, View):
    """Individual customer report (PDF only)."""
    
    def get(self, request, pk):
        customer = get_object_or_404(
            Customer.objects.select_related('sales_person').prefetch_related('documents', 'security_cheques'),
            pk=pk
        )
        
        # Check permissions
        if not request.user.is_admin_user:
            if not (request.user.is_sales_person_user and 
                    hasattr(request.user, 'sales_person') and 
                    customer.sales_person == request.user.sales_person):
                messages.error(request, _('You do not have permission to view this customer.'))
                return redirect('customers:list')
        
        format_type = request.GET.get('format', 'pdf')
        
        if format_type == 'pdf':
            buffer = generate_individual_customer_pdf(customer)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            filename = f'{customer.company_name.replace(" ", "_")}_customer_record_{date.today()}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        
        # HTML print view
        return render(request, 'customers/print.html', {
            'customer': customer,
            'tl_days_left': customer.get_trade_license_days_left(),
            'tl_status': customer.get_trade_license_status(),
            'passport_days_left': customer.get_passport_days_left(),
            'passport_status': customer.get_passport_status(),
            'eid_days_left': customer.get_eid_days_left(),
            'eid_status': customer.get_eid_status(),
            'print_date': date.today(),
        })