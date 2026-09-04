"""
Views for notifications app.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, View

from .forms import NotificationPreferenceForm
from .models import Notification, NotificationPreference


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = 25
    
    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).exclude(status=Notification.Status.DISMISSED).select_related('customer')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = self.get_queryset().filter(status=Notification.Status.UNREAD).count()
        # Last notification created_at gives a rough "last scan" timestamp.
        latest = self.get_queryset().order_by('-created_at').first()
        context['last_scan_at'] = latest.created_at if latest else None
        return context


class RefreshAlertsView(LoginRequiredMixin, View):
    """Re-run the expiry scan for the current user's scope and refresh."""

    def post(self, request):
        from .services import run_expiry_scan

        result = run_expiry_scan(user_scope=request.user, dry_run=False)

        messages.success(
            request,
            _(
                'Expiry alerts refreshed: %(created)d added, %(dismissed)d stale alerts cleared.'
            ) % {
                'created': result['created_count'],
                'dismissed': result['dismissed_count'],
            },
        )
        return redirect('notifications:list')


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.mark_as_read()
        
        if request.headers.get('HX-Request'):
            return JsonResponse({'status': 'ok'})
        return redirect('notifications:list')


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(
            user=request.user,
            status=Notification.Status.UNREAD
        ).update(status=Notification.Status.READ, read_at=timezone.now())
        
        messages.success(request, _('All notifications marked as read.'))
        return redirect('notifications:list')


class NotificationDismissView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.dismiss()
        
        if request.headers.get('HX-Request'):
            return JsonResponse({'status': 'ok'})
        return redirect('notifications:list')


class NotificationPreferenceView(LoginRequiredMixin, View):
    """View and update notification preferences."""

    def get_instance(self, user):
        prefs, created = NotificationPreference.objects.get_or_create(user=user)
        return prefs

    def get(self, request):
        prefs = self.get_instance(request.user)
        form = NotificationPreferenceForm(instance=prefs)
        return render(request, 'notifications/preferences.html', {
            'form': form,
            'prefs': prefs,
        })

    def post(self, request):
        prefs = self.get_instance(request.user)
        form = NotificationPreferenceForm(request.POST, instance=prefs)

        if form.is_valid():
            form.save()
            messages.success(request, _('Notification preferences updated.'))
            return redirect('notifications:preferences')

        return render(request, 'notifications/preferences.html', {
            'form': form,
            'prefs': prefs,
        })