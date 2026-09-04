"""
URL configuration for customer_records project.
"""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

from reports import views as reports_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # The root address (site home) shows the dashboard.
    path('', RedirectView.as_view(pattern_name='dashboard', permanent=False)),
    # Dashboard lives at the clean top-level /dashboard/ URL.
    path('dashboard/', reports_views.ReportsDashboardView.as_view(), name='dashboard'),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('customers/', include('customers.urls', namespace='customers')),
    path('documents/', include('documents.urls', namespace='documents')),
    path('salespersons/', include('salespersons.urls', namespace='salespersons')),
    path('cheques/', include('security_cheques.urls', namespace='security_cheques')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('audit/', include('audit.urls', namespace='audit')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)