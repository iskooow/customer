"""
URLs for security_cheques app.
"""

from django.urls import path

from . import views

app_name = 'security_cheques'

urlpatterns = [
    path('', views.SecurityChequeListView.as_view(), name='list'),
    path('customer/<int:customer_pk>/add/', views.SecurityChequeCreateView.as_view(), name='add'),
    path('<int:pk>/edit/', views.SecurityChequeUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.SecurityChequeDeleteView.as_view(), name='delete'),
    path('<int:pk>/download/', views.SecurityChequeDownloadView.as_view(), name='download'),
    path('bulk-update/', views.SecurityChequeBulkUpdateView.as_view(), name='bulk_update'),
]