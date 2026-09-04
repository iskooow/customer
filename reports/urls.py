"""
URLs for reports app.
"""

from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'reports'

urlpatterns = [
    # The dashboard now lives at the top-level /dashboard/ URL (see config/urls.py).
    # Redirect the legacy /reports/ root here so old links/bookmarks still work.
    path('', RedirectView.as_view(pattern_name='dashboard', permanent=False), name='report_root'),
    path('index/', views.ReportsIndexView.as_view(), name='index'),
    path('customers/', views.CustomerReportView.as_view(), name='customer_report'),
    path('expired/', views.ExpiredDocumentsReportView.as_view(), name='expired_documents'),
    path('expiring/', views.ExpiringDocumentsReportView.as_view(), name='expiring_documents'),
    path('missing/', views.MissingDocumentsReportView.as_view(), name='missing_documents'),
    path('salespersons/', views.SalespersonReportView.as_view(), name='salesperson_report'),
    path('cheques/', views.SecurityChequeReportView.as_view(), name='cheque_report'),
    path('customer/<int:pk>/', views.IndividualCustomerReportView.as_view(), name='customer_detail'),
]