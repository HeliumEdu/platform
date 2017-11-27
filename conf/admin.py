"""
Customize the Admin site.
"""
from django.conf import settings
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class UserAdmin(admin.UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('email', 'first_name', 'last_name', 'state', 'last_login', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'address_1', 'address_2',
                                      'city', 'state', 'postal_code', 'country', 'phone')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    def get_readonly_fields(self, request, obj=None):
        return 'date_joined', 'last_login'


class PlatformAdminSite(AdminSite):
    site_header = settings.PROJECT_NAME + ' Administration'
    site_title = site_header
    index_title = settings.PROJECT_NAME
    login_template = 'authentication/login.html'


# Instantiate the Admin site
admin_site = PlatformAdminSite()

# Register the models in the Admin
admin_site.register(get_user_model(), UserAdmin)
