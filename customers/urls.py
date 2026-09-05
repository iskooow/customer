"""
URLs for customers app.
"""

from django.urls import path

from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.CustomerListView.as_view(), name='list'),
    path('add/', views.CustomerCreateView.as_view(), name='add'),
    path('import/', views.CustomerImportView.as_view(), name='import'),
    path('import/preview/', views.CustomerImportPreviewView.as_view(), name='import_preview'),
    path('import/status/', views.CustomerImportStatusView.as_view(), name='import_status'),
    path('export/', views.CustomerExportView.as_view(), name='export'),
    path('<int:pk>/', views.CustomerDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='delete'),
    path('<int:pk>/print/', views.CustomerPrintView.as_view(), name='print'),
    path('<int:pk>/row/', views.customer_row_partial, name='row_partial'),
]