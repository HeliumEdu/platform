from django import forms
from django.contrib.admin import ModelAdmin
from django.contrib.auth import admin, password_validation
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core import exceptions
from rest_framework.authtoken.models import Token

from helium.auth.models import UserProfile
from helium.auth.models import UserSettings
from helium.common.admin import admin_site, BaseModelAdmin

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'


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
        super(UserCreationForm, self).save(commit)

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


class UserSettingsAdmin(BaseModelAdmin):
    list_display = ['get_user', 'time_zone', 'default_view', 'receive_emails_from_admin']
    list_filter = ['default_view', 'week_starts_on', 'receive_emails_from_admin']
    search_fields = ('user__email', 'user__username')
    ordering = ('user__username',)
    readonly_fields = ('user', 'created_at', 'updated_at')

    def get_user(self, obj):
        if obj.user:
            return obj.user.get_username()
        else:
            return ''

    def has_add_permission(self, request):
        return False

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


class UserProfileAdmin(BaseModelAdmin):
    list_display = ['get_user', 'phone', 'phone_verified']
    search_fields = ('user__email', 'user__username')
    ordering = ('user__username',)
    readonly_fields = ('user', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False

    def get_user(self, obj):
        if obj.user:
            return obj.user.get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


class TokenAdmin(ModelAdmin):
    list_display = ['get_user', 'key']
    search_fields = ('key', 'user__email', 'user__username')
    ordering = ('user__username',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('user',)
        return self.readonly_fields

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
admin_site.register(Token, TokenAdmin)
