"""
Views for accounts app.
"""

from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django.utils.translation import gettext_lazy as _

from .forms import UserRegistrationForm, UserProfileForm, UserUpdateForm
from .models import User


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        messages.success(self.request, _('Welcome back!'))
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, _('Invalid email or password.'))
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    next_page = 'accounts:login'
    
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, _('You have been logged out.'))
        return super().dispatch(request, *args, **kwargs)


class UserRegistrationView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('customers:list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, _('Account created successfully!'))
        return response


class UserProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'
    
    def get_object(self):
        return self.request.user


class UserProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self):
        return self.request.user
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Ensure uploaded files are passed to the form (multipart form data).
        if self.request.method in ('POST', 'PUT', 'PATCH'):
            kwargs['files'] = self.request.FILES
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, _('Profile updated successfully.'))
        return super().form_valid(form)


class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 25
    
    def get_queryset(self):
        if not self.request.user.is_admin_user:
            return User.objects.none()
        return User.objects.select_related('sales_person').order_by('-date_joined')


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/user_form.html'
    context_object_name = 'user_obj'
    success_url = reverse_lazy('accounts:user_list')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin_user:
            messages.error(request, _('You do not have permission to edit users.'))
            return redirect('accounts:user_list')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        messages.success(self.request, _('User updated successfully.'))
        return super().form_valid(form)