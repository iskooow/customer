"""
URLs for documents app.
"""

from django.urls import path

from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.DocumentListView.as_view(), name='list'),
    path('customer/<int:customer_pk>/upload/', views.DocumentUploadView.as_view(), name='upload'),
    path('<int:pk>/edit/', views.DocumentUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.DocumentDeleteView.as_view(), name='delete'),
    path('<int:pk>/download/', views.DocumentDownloadView.as_view(), name='download'),
    path('<int:pk>/view/', views.DocumentViewView.as_view(), name='view'),
]