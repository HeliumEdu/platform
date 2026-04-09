__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.conf import settings
from django.contrib import messages
from django.contrib.admin import ModelAdmin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.admin.sites import AdminSite
from django.shortcuts import redirect
from django.urls import reverse
from django_celery_results.models import TaskResult
from django_otp import devices_for_user
from two_factor.admin import AdminSiteOTPRequired
from two_factor.forms import AuthenticationTokenForm, BackupTokenForm

from helium.auth.utils.userutils import is_admin_allowed_email

_AdminBase = AdminSiteOTPRequired if settings.ADMIN_ENFORCE_2FA else AdminSite


class AdminLoginForm(AdminAuthenticationForm):
    error_messages = {
        **AdminAuthenticationForm.error_messages,
        'invalid_login': 'Check your admin credentials and try again.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'


class AdminTwoFactorLoginView:
    """Mixin-style class that injects AdminLoginForm into TwoFactorLoginView's auth step."""

    @classmethod
    def as_view(cls, **kwargs):
        from two_factor.views import LoginView as TwoFactorLoginView

        class _View(TwoFactorLoginView):
            form_list = (
                (TwoFactorLoginView.AUTH_STEP, AdminLoginForm),
                (TwoFactorLoginView.TOKEN_STEP, AuthenticationTokenForm),
                (TwoFactorLoginView.BACKUP_STEP, BackupTokenForm),
            )

        return _View.as_view(**kwargs)


class PlatformAdminSite(_AdminBase):
    """
    Creates a base AdminSite. On non-local environments, OTP (TOTP) is required and only users whose email domain is
    in ADMIN_ALLOWED_DOMAINS may access the admin. Authenticated users with no confirmed TOTP device are redirected
    to the setup flow.
    """
    site_header = settings.PROJECT_NAME + ' Administration'
    site_title = site_header
    index_title = settings.PROJECT_NAME
    login_form = AdminLoginForm

    def has_permission(self, request):
        if not super().has_permission(request):
            return False
        if not settings.ADMIN_ENFORCE_2FA:
            return True
        return is_admin_allowed_email(getattr(request.user, 'email', ''))

    def login(self, request, extra_context=None):
        # If authenticated but lacking admin permission, log out to prevent redirect loops
        if request.user.is_authenticated and not self.has_permission(request):
            from django.contrib.auth import logout
            logout(request)

        if not settings.ADMIN_ENFORCE_2FA:
            return super().login(request, extra_context)

        if request.user.is_authenticated and not any(devices_for_user(request.user)):
            return redirect(f"{reverse('two_factor:setup')}?next={request.get_full_path()}")
        return AdminTwoFactorLoginView.as_view()(request)


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

    def has_add_permission(self, request):
        return False


admin_site.register(TaskResult, TaskResultAdmin)


class EmailReputationEventAdmin(ModelAdmin):
    list_display = ('created_at', 'get_user', 'email_type', 'event_type', 'event_subtype')
    list_filter = ('event_type', 'email_type')
    search_fields = ('email_hash', 'user__email', 'user__username', 'sns_message_id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'user', 'email_hash', 'email_type', 'event_type', 'event_subtype', 'sns_message_id')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_user(self, obj):
        return obj.user.email if obj.user else '—'

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__email'


def suppress_selected_emails(modeladmin, request, queryset):
    """
    Django Admin action: add the selected email addresses to the SES suppression list
    with reason COMPLAINT. Only rows with a resolved user FK can be actioned; unresolved
    hashes (no matched account) are skipped with a warning.
    """
    from helium.common.utils.commonutils import add_to_ses_suppression_list

    suppressed = []
    skipped = 0

    for summary in queryset.select_related('user'):
        if summary.user:
            add_to_ses_suppression_list(summary.user.email, reason='COMPLAINT')
            suppressed.append(summary.user.email)
        else:
            skipped += 1

    if suppressed:
        modeladmin.message_user(
            request,
            f"Suppressed {len(suppressed)} address(es): {', '.join(suppressed)}",
            messages.SUCCESS,
        )
    if skipped:
        modeladmin.message_user(
            request,
            f"{skipped} row(s) skipped — no linked user account (cannot resolve email from hash alone).",
            messages.WARNING,
        )


suppress_selected_emails.short_description = "Add selected to SES suppression list (COMPLAINT)"


class EmailReputationSummaryAdmin(ModelAdmin):
    list_display = (
        'get_user', 'hard_bounce_count', 'soft_bounce_count', 'complaint_count',
        'last_event_type', 'last_event_at', 'updated_at',
    )
    list_filter = ('last_event_type',)
    search_fields = ('email_hash', 'user__email', 'user__username')
    ordering = ('-updated_at',)
    readonly_fields = (
        'created_at', 'updated_at', 'user', 'email_hash',
        'hard_bounce_count', 'soft_bounce_count', 'complaint_count',
        'last_event_at', 'last_event_type',
    )
    actions = [suppress_selected_emails]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_user(self, obj):
        return obj.user.email if obj.user else f'[no account — {obj.email_hash[:12]}…]'

    get_user.short_description = 'User / Hash'
    get_user.admin_order_field = 'user__email'


from helium.common.models import EmailReputationEvent, EmailReputationSummary

admin_site.register(EmailReputationEvent, EmailReputationEventAdmin)
admin_site.register(EmailReputationSummary, EmailReputationSummaryAdmin)
