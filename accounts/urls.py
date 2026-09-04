"""
URLs for accounts app.
"""

from django.urls import path
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/edit/', views.UserProfileUpdateView.as_view(), name='profile_edit'),
    path('password/change/', PasswordChangeView.as_view(template_name='accounts/password_change.html'), name='password_change'),
    path('password/change/done/', PasswordChangeDoneView.as_view(template_name='accounts/password_change_done.html'), name='password_change_done'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_edit'),
]