__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.conf import settings
from django.contrib import messages
from django.contrib.admin import ModelAdmin, SimpleListFilter
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.admin.sites import AdminSite
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from helium.common.models import TaskResultProxy
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


def staff_filter(user_field=None):
    """
    Factory returning a SimpleListFilter that splits records by staff status.
    Pass user_field as the FK path to the user (e.g. 'user', 'course_group__user').
    Omit for models where the queryset operates directly on the User model.
    """
    prefix = f'{user_field}__' if user_field else ''
    staff_q = (
        Q(**{f'{prefix}is_superuser': True}) |
        Q(**{f'{prefix}email__endswith': '@heliumedu.com'}) |
        Q(**{f'{prefix}email__endswith': '@heliumedu.dev'})
    )

    class _StaffFilter(SimpleListFilter):
        title = 'staff'
        parameter_name = 'staff'

        def lookups(self, request, model_admin):
            return [('yes', 'Staff'), ('no', 'Non-staff')]

        def queryset(self, request, queryset):
            if self.value() == 'yes':
                return queryset.filter(staff_q)
            if self.value() == 'no':
                return queryset.exclude(staff_q)
            return queryset

    return _StaffFilter


def has_course_schedule_filter(schedules_prefix):
    """
    Factory returning a SimpleListFilter that splits records by whether they have an active course schedule.
    Pass schedules_prefix as the FK path to the schedules relation (e.g. 'schedules', 'courses__schedules').
    """
    class _Filter(SimpleListFilter):
        title = 'has course schedule'
        parameter_name = 'has_course_schedule'

        def lookups(self, request, model_admin):
            return [('yes', 'Yes'), ('no', 'No')]

        def queryset(self, request, queryset):
            has_q = (
                Q(**{f'{schedules_prefix}__isnull': False}) &
                ~Q(**{f'{schedules_prefix}__days_of_week': '0000000'})
            )
            if self.value() == 'yes':
                return queryset.filter(has_q).distinct()
            if self.value() == 'no':
                return queryset.exclude(has_q).distinct()
            return queryset

    return _Filter


def has_weighted_grading_filter(weight_field):
    """
    Factory returning a SimpleListFilter that splits records by whether they use weighted grading.
    Pass weight_field as the FK path to the weight field (e.g. 'weight', 'categories__weight').
    """
    class _Filter(SimpleListFilter):
        title = 'has weighted grading'
        parameter_name = 'has_weighted_grading'

        def lookups(self, request, model_admin):
            return [('yes', 'Yes'), ('no', 'No')]

        def queryset(self, request, queryset):
            if self.value() == 'yes':
                return queryset.filter(**{f'{weight_field}__gt': 0}).distinct()
            if self.value() == 'no':
                return queryset.filter(**{f'{weight_field}': 0}).distinct()
            return queryset

    return _Filter


def has_credits_filter(credits_field):
    """
    Factory returning a SimpleListFilter that splits records by whether they have credits assigned.
    Pass credits_field as the FK path to the credits field (e.g. 'credits', 'course_groups__courses__credits').
    """
    class _Filter(SimpleListFilter):
        title = 'has credits'
        parameter_name = 'has_credits'

        def lookups(self, request, model_admin):
            return [('yes', 'Yes'), ('no', 'No')]

        def queryset(self, request, queryset):
            if self.value() == 'yes':
                return queryset.filter(**{f'{credits_field}__gt': 0}).distinct()
            if self.value() == 'no':
                return queryset.filter(**{f'{credits_field}': 0}).distinct()
            return queryset

    return _Filter


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
    list_filter = ('status', 'worker', 'date_done')
    search_fields = ('task_id', 'task_name')
    ordering = ('-date_done',)

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin_site.register(TaskResultProxy, TaskResultAdmin)


def suppress_selected_email_events(modeladmin, request, queryset):
    """Django Admin action: suppress the distinct email addresses from the selected events."""
    from helium.common.utils.commonutils import add_to_ses_suppression_list

    emails = list(queryset.values_list('email', flat=True).distinct())
    for email in emails:
        add_to_ses_suppression_list(email, reason='COMPLAINT')

    modeladmin.message_user(
        request,
        f"Suppressed {len(emails)} address(es): {', '.join(emails)}",
        messages.SUCCESS,
    )


suppress_selected_email_events.short_description = "Add selected to SES suppression list (COMPLAINT)"


class EmailReputationEventAdmin(ModelAdmin):
    list_display = ('created_at', 'email', 'email_type', 'event_type', 'event_subtype')
    list_filter = ('event_type', 'email_type', staff_filter('user'))
    search_fields = ('email', 'user__email', 'user__username', 'sns_message_id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'user', 'email', 'email_type', 'event_type', 'event_subtype', 'sns_message_id')
    actions = [suppress_selected_email_events]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


from helium.common.models import EmailReputationEvent

admin_site.register(EmailReputationEvent, EmailReputationEventAdmin)
