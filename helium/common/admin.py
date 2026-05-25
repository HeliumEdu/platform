__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.admin import ModelAdmin, SimpleListFilter
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.admin.sites import AdminSite
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django_otp import devices_for_user
from two_factor.admin import AdminSiteOTPRequired
from two_factor.forms import AuthenticationTokenForm, BackupTokenForm

from helium.auth.utils.userutils import is_admin_allowed_email
from helium.common.models import TaskResultProxy
from helium.common.periodic import PERIODIC_TASKS, format_schedule

logger = logging.getLogger(__name__)

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

    def get_urls(self):
        return [
            path('periodic-tasks/',
                 self.admin_view(self.periodic_tasks_view),
                 name='periodic-tasks'),
        ] + super().get_urls()

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        if app_label is None:
            tools_url = reverse('admin:periodic-tasks')
            app_list.append({
                'name': 'Tools',
                'app_label': 'helium_tools',
                'app_url': tools_url,
                'has_module_perms': True,
                'models': [
                    {
                        'name': 'Periodic tasks',
                        'object_name': 'PeriodicTask',
                        'admin_url': tools_url,
                        'view_only': True,
                    },
                ],
            })
        return app_list

    def periodic_tasks_view(self, request):
        triggerable = [s for s in PERIODIC_TASKS if s.manually_triggerable]

        if request.method == 'POST':
            task_name = request.POST.get('task', '')
            spec = next((s for s in triggerable if s.task.name == task_name), None)
            if spec is None:
                messages.error(request, f"Unknown or non-triggerable periodic task: {task_name}")
            else:
                kwargs = {}
                if spec.priority is not None:
                    kwargs['priority'] = spec.priority
                async_result = spec.task.apply_async(**kwargs)
                logger.info(f"Periodic task '{spec.task.name}' manually triggered by {request.user.email} "
                            f"(task_id={async_result.id})")
                messages.success(request,
                                 f"Queued '{spec.task.name}' (task id: {async_result.id}). "
                                 f"Results will appear in Task results events.")
            return HttpResponseRedirect(reverse('admin:periodic-tasks'))

        rows = sorted(
            ({'name': spec.task.name,
              'short_name': spec.task.name.rsplit('.', 1)[-1],
              'schedule': format_schedule(spec.schedule),
              'priority': spec.priority,
              'description': spec.description}
             for spec in triggerable),
            key=lambda r: r['name'],
        )
        context = {
            **self.each_context(request),
            'title': 'Periodic tasks',
            'tasks': rows,
        }
        return TemplateResponse(request, 'admin/periodic_tasks.html', context)


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


def prompt_for_review_filter(field_path):
    """
    Factory returning a SimpleListFilter that splits records by whether the user is queued for a review prompt.
    Pass field_path as the FK path to the boolean (e.g. 'prompt_for_review', 'settings__prompt_for_review').
    """

    class _Filter(SimpleListFilter):
        title = 'prompt for review'
        parameter_name = 'prompt_for_review'

        def lookups(self, request, model_admin):
            return [('yes', 'Yes'), ('no', 'No')]

        def queryset(self, request, queryset):
            if self.value() == 'yes':
                return queryset.filter(**{field_path: True})
            if self.value() == 'no':
                return queryset.filter(**{field_path: False})
            return queryset

    return _Filter


def review_prompts_requested_filter(field_path):
    """
    Factory returning a SimpleListFilter that buckets records by the count of review prompts requested from the OS.
    Pass field_path as the FK path to the integer (e.g. 'review_prompts_requested',
    'settings__review_prompts_requested').
    """

    class _Filter(SimpleListFilter):
        title = 'review prompts requested'
        parameter_name = 'review_prompts_requested'

        def lookups(self, request, model_admin):
            return [('never', 'Never'), ('once', 'Once'), ('multiple', 'Multiple')]

        def queryset(self, request, queryset):
            if self.value() == 'never':
                return queryset.filter(**{field_path: 0})
            if self.value() == 'once':
                return queryset.filter(**{field_path: 1})
            if self.value() == 'multiple':
                return queryset.filter(**{f'{field_path}__gte': 2})
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


class ObjectActionsMixin:
    """
    Mixin that renders per-object action buttons on the change form. Subclasses declare ``object_actions`` as a list
    of ``(action_func, 'Button label')`` tuples. Each action_func must accept the standard Django admin action
    signature ``(modeladmin, request, queryset)``.
    """
    object_actions = ()
    change_form_template = 'admin/object_actions_change_form.html'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['object_actions'] = [
            (func.__name__, label) for func, label in self.object_actions
        ]
        return super().change_view(request, object_id, form_url, extra_context)

    def response_change(self, request, obj):
        for func, label in self.object_actions:
            if f'_action_{func.__name__}' in request.POST:
                queryset = self.model.objects.filter(pk=obj.pk)
                func(self, request, queryset)
                return redirect(request.get_full_path())
        return super().response_change(request, obj)


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

    def _inject_extra_context(self, extra_context):
        extra_context = extra_context or {}
        extra_context.setdefault('show_save_and_add_another', False)
        return extra_context

    def add_view(self, request, form_url='', extra_context=None):
        return super().add_view(request, form_url, self._inject_extra_context(extra_context))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return super().change_view(request, object_id, form_url, self._inject_extra_context(extra_context))


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
    list_display = ('email', 'created_at', 'email_type', 'event_type', 'event_subtype')
    list_filter = ('event_type', 'email_type', 'event_subtype')
    search_fields = ('email', 'user__email', 'user__username', 'sns_message_id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'user', 'email', 'email_type', 'event_type', 'event_subtype', 'sns_message_id')
    actions = [suppress_selected_email_events]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


from helium.common.models import EmailReputationEvent

admin_site.register(EmailReputationEvent, EmailReputationEventAdmin)
