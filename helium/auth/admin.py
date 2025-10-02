__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

from django import forms
from django.contrib.auth import admin, password_validation
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core import exceptions
from rest_framework_simplejwt.token_blacklist.admin import OutstandingTokenAdmin, BlacklistedTokenAdmin
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from helium.auth.models import UserProfile
from helium.auth.models import UserSettings
from helium.auth.models.userpushtoken import UserPushToken
from helium.common.admin import admin_site, BaseModelAdmin


class AdminUserCreationForm(UserCreationForm):
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 != password2:
            raise forms.ValidationError("You must enter matching passwords.")

        try:
            password_validation.validate_password(password=password1, user=get_user_model())
        except exceptions.ValidationError as e:
            raise forms.ValidationError(list(e.messages))

        return password1

    def save(self, commit=True):
        super().save(commit)

        self.instance.is_active = True

        self.instance.save()

        return self.instance


class UserAdmin(admin.UserAdmin, BaseModelAdmin):
    form = UserChangeForm
    add_form = AdminUserCreationForm

    list_display = ('email', 'username', 'created_at', 'last_login', 'is_active')
    list_filter = (
        'is_active', 'profile__phone_verified', 'settings__default_view', 'settings__receive_emails_from_admin',)
    search_fields = ('email', 'username')
    ordering = ('-last_login',)
    add_fieldsets = (
        (None, {
            'fields': ('username', 'email', 'password1', 'password2',),
        }),
    )
    fieldsets = None
    filter_horizontal = ()

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('created_at', 'last_login',)

        return self.readonly_fields


class UserProfileAdmin(BaseModelAdmin):
    list_display = ['phone', 'phone_verified', 'get_user']
    search_fields = ('user__email', 'user__username')
    ordering = ('user__username',)
    readonly_fields = ('user',)

    def has_add_permission(self, request):
        return False

    def get_user(self, obj):
        if obj.user:
            return obj.user.get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


class UserSettingsAdmin(BaseModelAdmin):
    list_display = ['time_zone', 'default_view', 'receive_emails_from_admin', 'get_user']
    list_filter = ['default_view', 'week_starts_on', 'receive_emails_from_admin']
    search_fields = ('user__email', 'user__username')
    ordering = ('user__username',)
    readonly_fields = ('user',)

    def get_user(self, obj):
        if obj.user:
            return obj.user.get_username()
        else:
            return ''

    def has_add_permission(self, request):
        return False

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


class UserPushTokenAdmin(BaseModelAdmin):
    list_display = ['device_id', 'token', 'get_user']
    search_fields = ('user__email', 'user__username')
    ordering = ('user__username',)

    def get_user(self, obj):
        if obj.user:
            return obj.user.get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


# Register the models in the Admin
admin_site.register(get_user_model(), UserAdmin)
admin_site.register(UserProfile, UserProfileAdmin)
admin_site.register(UserSettings, UserSettingsAdmin)
admin_site.register(UserPushToken, UserPushTokenAdmin)
admin_site.register(OutstandingToken, OutstandingTokenAdmin)
admin_site.register(BlacklistedToken, BlacklistedTokenAdmin)
