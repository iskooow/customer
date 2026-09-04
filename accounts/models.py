"""
Custom User model for the Customer Records Management System.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom user model with role-based permissions.
    """
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Admin')
        SALES_PERSON = 'sales_person', _('Sales Person')
    
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=Role.choices,
        default=Role.SALES_PERSON,
    )
    phone = models.CharField(_('phone'), max_length=20, blank=True)
    logo = models.ImageField(
        _('company logo'),
        upload_to='logos/',
        blank=True,
        null=True,
        help_text=_('Upload or update your company logo. Recommended: PNG or JPG, max 5MB.'),
    )
    is_active = models.BooleanField(_('active'), default=True)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    
    # Sales person relation (for sales person users)
    sales_person = models.OneToOneField(
        'salespersons.SalesPerson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_account',
        verbose_name=_('sales person profile'),
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.get_full_name() or self.email
    
    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN or self.is_superuser
    
    @property
    def is_sales_person_user(self):
        return self.role == self.Role.SALES_PERSON
    
    def get_assigned_customers(self):
        """Get customers assigned to this sales person."""
        if self.is_sales_person_user and self.sales_person:
            return self.sales_person.customers.all()
        return self.customers.all() if self.is_admin_user else None