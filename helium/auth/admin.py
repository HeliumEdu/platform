from django import forms
from django.contrib.admin import ModelAdmin
from django.contrib.auth import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from helium.auth.models import UserProfile
from helium.auth.models import UserSettings
from helium.auth.utils.userutils import validate_password
from helium.common.admin import admin_site

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


class AdminUserCreationForm(UserCreationForm):
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        error = validate_password(password1, password2)

        if error:
            raise forms.ValidationError(error)

        return password2

    def save(self, commit=True):
        super(UserCreationForm, self).save(commit)

        self.instance.is_active = True

        self.instance.save()

        return self.instance


class UserAdmin(admin.UserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = AdminUserCreationForm

    list_display = ('email', 'username', 'created_at', 'last_login',)
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


class UserSettingsAdmin(ModelAdmin):
    list_display = ['get_user', 'time_zone', 'default_view', 'receive_emails_from_admin']
    list_filter = ['default_view', 'week_starts_on', 'receive_emails_from_admin']
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


class UserProfileAdmin(ModelAdmin):
    list_display = ['get_user', 'phone_carrier']
    list_filter = ('phone_carrier',)
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


# Register the models in the Admin
admin_site.register(get_user_model(), UserAdmin)
admin_site.register(UserSettings, UserSettingsAdmin)
admin_site.register(UserProfile, UserProfileAdmin)
