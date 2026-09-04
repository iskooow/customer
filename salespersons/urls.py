"""
URLs for salespersons app.
"""

from django.urls import path

from . import views

app_name = 'salespersons'

urlpatterns = [
    path('', views.SalesPersonListView.as_view(), name='list'),
    path('add/', views.SalesPersonCreateView.as_view(), name='add'),
    path('<int:pk>/', views.SalesPersonDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.SalesPersonUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.SalesPersonDeleteView.as_view(), name='delete'),
    path('<int:pk>/toggle/', views.SalesPersonToggleActiveView.as_view(), name='toggle_active'),
    path('<int:pk>/assign/', views.SalesPersonCustomerAssignView.as_view(), name='assign_customers'),
]