"""
URLs for notifications app.
"""

from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='list'),
    path('refresh/', views.RefreshAlertsView.as_view(), name='refresh'),

    path('<int:pk>/read/', views.NotificationMarkReadView.as_view(), name='mark_read'),
    path('all/read/', views.NotificationMarkAllReadView.as_view(), name='mark_all_read'),
    path('<int:pk>/dismiss/', views.NotificationDismissView.as_view(), name='dismiss'),
    path('preferences/', views.NotificationPreferenceView.as_view(), name='preferences'),
]