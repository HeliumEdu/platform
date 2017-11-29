"""
Customize the Admin site.
"""

from django.contrib.admin import ModelAdmin
from django.contrib.auth import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from helium.common.admin import admin_site
from helium.users.models import UserProfile
from helium.users.models import UserSetting

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class UserAdmin(admin.UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('email', 'username', 'last_login', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email', 'username')
    ordering = ('email',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    def get_readonly_fields(self, request, obj=None):
        return 'date_joined', 'last_login'


class UserSettingAdmin(ModelAdmin):
    model = UserSetting
    list_display = ['get_user', 'time_zone']
    ordering = ('user__username',)
    readonly_fields = ('user',)

    def get_user(self, obj):
        if obj.user:
            return obj.user.username
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


class UserProfileAdmin(ModelAdmin):
    model = UserProfile
    list_display = ['get_user']
    list_filter = ('phone_carrier',)
    ordering = ('user__username',)
    readonly_fields = ('user',)

    def get_user(self, obj):
        if obj.user:
            return obj.user.username
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


# Register the models in the Admin
admin_site.register(get_user_model(), UserAdmin)
admin_site.register(UserSetting, UserSettingAdmin)
admin_site.register(UserProfile, UserProfileAdmin)
