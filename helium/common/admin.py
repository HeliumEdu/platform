__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.conf import settings
from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.shortcuts import redirect
from django.urls import reverse
from django_celery_results.models import TaskResult
from django_otp import devices_for_user
from two_factor.admin import AdminSiteOTPRequired

from helium.auth.utils.userutils import is_admin_allowed_email

_AdminBase = AdminSite if 'local' in settings.ENVIRONMENT else AdminSiteOTPRequired


class PlatformAdminSite(_AdminBase):
    """
    Creates a base AdminSite. On non-local environments, OTP (TOTP) is required and only users whose email domain is
    in ADMIN_ALLOWED_DOMAINS may access the admin. Authenticated users with no confirmed TOTP device are redirected
    to the setup flow.
    """
    site_header = settings.PROJECT_NAME + ' Administration'
    site_title = site_header
    index_title = settings.PROJECT_NAME

    def has_permission(self, request):
        if not super().has_permission(request):
            return False
        if 'local' in settings.ENVIRONMENT:
            return True
        return is_admin_allowed_email(getattr(request.user, 'email', ''))

    def login(self, request, extra_context=None):
        # If authenticated but lacking admin permission, log out to prevent redirect loops
        if request.user.is_authenticated and not self.has_permission(request):
            from django.contrib.auth import logout
            logout(request)

        if 'local' in settings.ENVIRONMENT:
            return super().login(request, extra_context)

        from two_factor.views import LoginView as TwoFactorLoginView
        if request.user.is_authenticated and not any(devices_for_user(request.user)):
            return redirect(f"{reverse('two_factor:setup')}?next={request.get_full_path()}")
        return TwoFactorLoginView.as_view()(request)


class BaseModelAdmin(ModelAdmin):
    """
    All Models that inherit from BaseModel should also inherit from this BaseModelAdmin, which makes sure the common
    attributes are properly rendered in the admin area.
    """
    list_display = ('created_at', 'updated_at',)
    ordering = ('-updated_at',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('created_at', 'updated_at',)

        return self.readonly_fields


# Instantiate the Admin site
admin_site = PlatformAdminSite()


class TaskResultAdmin(ModelAdmin):
    list_display = ('task_id', 'task_name', 'date_done', 'status', 'worker')
    list_filter = ('status', 'date_done')
    search_fields = ('task_id', 'task_name')
    ordering = ('-date_done',)


admin_site.register(TaskResult, TaskResultAdmin)
