"""
User admin site.
"""

from django.contrib.admin import ModelAdmin
from django.contrib.auth import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from helium.common.admin import admin_site
from helium.users.models import UserProfile
from helium.users.models import UserSettings

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class UserAdmin(admin.UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('email', 'username', 'created_at', 'last_login',)
    list_filter = (
        'is_active', 'profile__phone_verified', 'settings__default_view', 'settings__receive_emails_from_admin',)
    search_fields = ('email', 'username')
    ordering = ('-last_login',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    fieldsets = (
        (None, {'fields': ('email', 'password', 'is_active', 'is_superuser', 'last_login', 'created_at')}),
    )
    filter_horizontal = ()

    def get_readonly_fields(self, request, obj=None):
        return 'created_at', 'last_login'


class UserSettingsAdmin(ModelAdmin):
    model = UserSettings
    list_display = ['get_user', 'time_zone', 'default_view', 'receive_emails_from_admin']
    list_filter = ['default_view', 'week_starts_on', 'receive_emails_from_admin']
    ordering = ('user__username',)
    readonly_fields = ('user',)

    def get_user(self, obj):
        if obj.user:
            return obj.user.get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


class UserProfileAdmin(ModelAdmin):
    model = UserProfile
    list_display = ['get_user', 'phone_carrier']
    list_filter = ('phone_carrier',)
    ordering = ('user__username',)
    readonly_fields = ('user',)

    def get_user(self, obj):
        if obj.user:
            return obj.user.get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


# Register the models in the Admin
admin_site.register(get_user_model(), UserAdmin)
admin_site.register(UserSettings, UserSettingsAdmin)
admin_site.register(UserProfile, UserProfileAdmin)
