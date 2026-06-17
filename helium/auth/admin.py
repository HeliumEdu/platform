__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib import admin as django_admin
from django.contrib import messages
from django.contrib.admin import SimpleListFilter
from django.contrib.auth import admin, password_validation
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import exceptions
from django.db.models import Count, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework_simplejwt.token_blacklist.admin import OutstandingTokenAdmin, BlacklistedTokenAdmin
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from helium.auth.models import UserProfile
from helium.auth.models import UserSettings
from helium.auth.models.tokenproxy import BlacklistedTokenProxy, OutstandingTokenProxy
from helium.auth.models.userclientactivity import UserClientActivity
from helium.auth.models.useroauthprovider import UserOAuthProvider
from helium.auth.models.userpushtoken import UserPushToken
from helium.auth.tasks import send_password_reset_email, send_dormant_user_warning_email
from helium.auth.utils.userutils import is_admin_allowed_email
from helium.common.admin import admin_site, BaseModelAdmin, ObjectActionsMixin, staff_filter, \
    has_course_schedule_filter, has_credits_filter, has_weighted_grading_filter, prompt_for_review_filter, \
    review_prompts_requested_filter, logged_action
from helium.common.utils.commonutils import clear_ses_suppression_if_exists
from helium.feed.models.externalcalendar import ExternalCalendar
from helium.planner.models.attachment import Attachment
from helium.planner.models.course import Course
from helium.planner.models.coursegroup import CourseGroup
from helium.planner.models.event import Event
from helium.planner.models.homework import Homework
from helium.planner.models.note import Note
from helium.planner.services.reminderservice import heal_orphaned_repeating_reminders
from helium.common.utils import taskutils
from helium.planner.tasks import recalculate_course_grades_for_course_group


class AdminUserChangeForm(UserChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use non-standard IDs so password managers don't autofill these fields
        for field_name, field_id in (('username', 'ha_un'), ('email', 'ha_em'), ('email_changing', 'ha_emc')):
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({'id': field_id, 'autocomplete': 'new-password'})
        if self.instance and self.instance.pk and 'username' in self.fields:
            self.fields['username'].disabled = True

    def clean_email(self):
        UserModel = get_user_model()
        email = self.cleaned_data.get('email')
        if self.instance and email != self.instance.email:
            # Check uniqueness against both email and email_changing fields
            if UserModel.objects.email_used(self.instance.pk, email):
                raise forms.ValidationError("Sorry, that email is already in use.")
            if self.instance.is_superuser:
                if not is_admin_allowed_email(email):
                    raise forms.ValidationError(
                        f"Admin email must be within an allowed domain ({', '.join(settings.ADMIN_ALLOWED_DOMAINS)}).")
        return email


class AdminUserCreationForm(UserCreationForm):
    def clean_password2(self):
        UserModel = get_user_model()
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 != password2:
            raise forms.ValidationError("You must enter matching passwords.")

        try:
            password_validation.validate_password(password=password1, user=UserModel)
        except exceptions.ValidationError as e:
            raise forms.ValidationError(list(e.messages))

        return password1

    def save(self, commit=True):
        super().save(commit)

        self.instance.is_active = True

        self.instance.save()

        return self.instance


class OAuthProviderFilter(SimpleListFilter):
    title = 'OAuth provider'
    parameter_name = 'oauth_provider'

    def lookups(self, request, model_admin):
        return [('none', 'None (password only)')] + list(UserOAuthProvider.PROVIDER_CHOICES)

    def queryset(self, request, queryset):
        if self.value() == 'none':
            return queryset.filter(oauth_providers__isnull=True)
        elif self.value():
            return queryset.filter(oauth_providers__provider=self.value()).distinct()
        return queryset


class ClientFilter(SimpleListFilter):
    title = 'client activity'
    parameter_name = 'client'

    def lookups(self, request, model_admin):
        return (
            ('web', 'Web'),
            ('mobile_app', 'Mobile'),
            ('both', 'Both'),
        )

    def queryset(self, request, queryset):
        web = UserClientActivity.CLIENT_WEB
        mobile = UserClientActivity.CLIENT_MOBILE_APP
        if self.value() == 'web':
            return queryset.filter(client_activity__client=web).distinct()
        elif self.value() == 'mobile_app':
            return queryset.filter(client_activity__client=mobile).distinct()
        elif self.value() == 'both':
            return queryset.filter(client_activity__client=web) \
                           .filter(client_activity__client=mobile).distinct()
        return queryset


class ActiveStatusFilter(SimpleListFilter):
    title = 'active'
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active'),
            ('dormant', 'Dormant'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(deletion_warning_sent_at__isnull=True, is_active=True)
        elif self.value() == 'dormant':
            return queryset.filter(deletion_warning_sent_at__isnull=False)
        return queryset


class PendingDeletionFilter(SimpleListFilter):
    title = 'pending deletion'
    parameter_name = 'pending_deletion'

    def lookups(self, request, model_admin):
        return (
            ('pending', 'Pending deletion'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'pending':
            return queryset.filter(deletion_requested_at__isnull=False)
        return queryset


class UserOAuthProviderInline(django_admin.TabularInline):
    model = UserOAuthProvider
    extra = 0
    can_delete = True
    fields = ('provider', 'provider_user_id', 'created_at', 'last_used_at')
    readonly_fields = ('provider', 'provider_user_id', 'created_at', 'last_used_at')

    def has_add_permission(self, request, obj=None):
        return False


class UserPushTokenInline(django_admin.TabularInline):
    model = UserPushToken
    extra = 0
    can_delete = True
    fields = ('device_id', 'created_at', 'updated_at')
    readonly_fields = ('device_id', 'created_at', 'updated_at')

    def has_add_permission(self, request, obj=None):
        return False


@logged_action
@django_admin.action(description='Mark selected users as email verified')
def mark_email_verified(modeladmin, request, queryset):
    updated = queryset.filter(is_active=False).update(is_active=True)
    modeladmin.message_user(request, f'{updated} user(s) marked as verified.')


@logged_action
@django_admin.action(description='Send password reset email to selected users')
def send_password_reset(modeladmin, request, queryset):
    sent, skipped = 0, 0
    for user in queryset:
        if not user.has_usable_password():
            skipped += 1
            continue
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = PasswordResetTokenGenerator().make_token(user)
        reset_url = f"{settings.PROJECT_APP_HOST}/forgot/confirm?uid={uid}&token={token}"
        taskutils.safe_apply_async(
            send_password_reset_email,
            args=(user.email, reset_url),
            priority=settings.CELERY_PRIORITY_HIGH,
        )
        sent += 1
    modeladmin.message_user(request, f'Password reset sent to {sent} user(s).')
    if skipped:
        modeladmin.message_user(
            request,
            f'{skipped} OAuth-only user(s) skipped (no password to reset).',
            messages.WARNING,
        )


@logged_action
@django_admin.action(description='Purge push tokens for selected users')
def purge_push_tokens(modeladmin, request, queryset):
    deleted, _ = UserPushToken.objects.filter(user__in=queryset).delete()
    modeladmin.message_user(request, f'{deleted} push token(s) deleted.')


@logged_action
@django_admin.action(description='Send dormant warning email to selected users')
def send_dormant_warning(modeladmin, request, queryset):
    queued, skipped = 0, 0
    for user in queryset:
        if user.deletion_warning_count >= 4:
            skipped += 1
            continue
        taskutils.safe_apply_async(
            send_dormant_user_warning_email,
            args=(user.pk,),
            priority=settings.CELERY_PRIORITY_LOW,
        )
        queued += 1
    modeladmin.message_user(request, f'Dormant warning email queued for {queued} user(s).')
    if skipped:
        modeladmin.message_user(
            request,
            f'{skipped} user(s) skipped (already at max warnings).',
            messages.WARNING,
        )


@logged_action
@django_admin.action(description='Recalculate all grades for selected users')
def recalculate_all_grades(modeladmin, request, queryset):
    count = 0
    for cg_id in CourseGroup.objects.filter(user__in=queryset).values_list('id', flat=True):
        taskutils.safe_apply_async(
            recalculate_course_grades_for_course_group,
            args=(cg_id,),
            priority=settings.CELERY_PRIORITY_LOW,
        )
        count += 1
    modeladmin.message_user(request, f'Grade recalculation queued for {count} course group(s).')


@logged_action
@django_admin.action(description='Heal orphaned repeating reminders for selected users')
def heal_orphaned_reminders(modeladmin, request, queryset):
    for user in queryset:
        heal_orphaned_repeating_reminders(user_id=user.pk)
    modeladmin.message_user(request, f'Orphaned reminders healed for {queryset.count()} user(s).')


@logged_action
@django_admin.action(description='Disable feeds for selected users')
def disable_feeds(modeladmin, request, queryset):
    updated = UserSettings.objects.filter(user__in=queryset, private_slug__isnull=False).update(private_slug=None)
    modeladmin.message_user(request, f'Feeds disabled for {updated} user(s).')


@logged_action
@django_admin.action(description="Reset \"What's New\" for selected users")
def reset_whats_new(modeladmin, request, queryset):
    updated = UserSettings.objects.filter(user__in=queryset).update(whats_new_version_seen=0)
    modeladmin.message_user(request, f'"What\'s New" reset for {updated} user(s).')


@logged_action
@django_admin.action(description='Trigger review prompt for selected users')
def force_review_prompt(modeladmin, request, queryset):
    updated = UserSettings.objects.filter(user__in=queryset).update(prompt_for_review=True)
    modeladmin.message_user(request, f'Review prompt triggered for {updated} user(s).')


@logged_action
@django_admin.action(description='Force logout selected users (invalidates next token refresh)')
def force_logout(modeladmin, request, queryset):
    tokens = OutstandingToken.objects.filter(user__in=queryset)
    for token in tokens:
        BlacklistedToken.objects.get_or_create(token=token)
    modeladmin.message_user(request, f'Logged out {queryset.count()} user(s).')


@logged_action
@django_admin.action(description='Trigger review prompt for users of selected activities')
def force_review_prompt_for_activities(modeladmin, request, queryset):
    user_ids = queryset.values_list('user_id', flat=True).distinct()
    updated = UserSettings.objects.filter(user_id__in=user_ids).update(prompt_for_review=True)
    modeladmin.message_user(request, f'Review prompt triggered for {updated} user(s).')


@logged_action
@django_admin.action(description='Force logout users of selected activities (invalidates next token refresh)')
def force_logout_for_activities(modeladmin, request, queryset):
    user_ids = list(queryset.values_list('user_id', flat=True).distinct())
    tokens = OutstandingToken.objects.filter(user_id__in=user_ids)
    for token in tokens:
        BlacklistedToken.objects.get_or_create(token=token)
    modeladmin.message_user(request, f'Logged out {len(user_ids)} user(s).')


@logged_action
@django_admin.action(description='Remove selected users from SES suppression list')
def remove_from_ses_suppression(modeladmin, request, queryset):
    cleared, not_suppressed = [], []
    for user in queryset:
        if clear_ses_suppression_if_exists(user.email):
            cleared.append(user.email)
        else:
            not_suppressed.append(user.email)
    if cleared:
        modeladmin.message_user(request, f'Removed {len(cleared)} user(s) from suppression list.')
    if not_suppressed:
        modeladmin.message_user(
            request,
            f'{len(not_suppressed)} user(s) were not on the suppression list.',
            messages.INFO,
        )


class UserAdmin(ObjectActionsMixin, admin.UserAdmin, BaseModelAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm

    list_display = ('email', 'last_activity', 'get_auth_type',
                    'num_notes', 'num_courses', 'num_homework', 'num_events',
                    'num_attachments', 'num_external_calendars', 'last_login_legacy',
                    'deletion_warning_count', 'deletion_requested_at', 'mobile_app_usage_percent_30d',
                    'created_at', 'is_power_user', 'is_active')
    list_filter = (ActiveStatusFilter, PendingDeletionFilter, 'is_power_user',
                   'settings__show_getting_started',
                   'settings__default_view', 'settings__remember_filter_state',
                   'settings__calendar_event_limit', 'settings__default_reminder_type',
                   'settings__color_scheme_theme', 'settings__calendar_use_category_colors',
                   OAuthProviderFilter, ClientFilter,
                   has_weighted_grading_filter('course_groups__courses__categories__weight'),
                   has_credits_filter('course_groups__courses__credits'),
                   has_course_schedule_filter('course_groups__courses__schedules'),
                   prompt_for_review_filter('settings__prompt_for_review'),
                   review_prompts_requested_filter('settings__review_prompts_requested'), staff_filter())
    search_fields = ('id', 'email', 'username', 'email_changing')
    ordering = ('-last_activity',)
    add_fieldsets = (
        (None, {
            'fields': ('username', 'email', 'password1', 'password2',),
        }),
    )
    fieldsets = None
    filter_horizontal = ()
    actions = [mark_email_verified, send_password_reset, purge_push_tokens, force_logout,
               send_dormant_warning, recalculate_all_grades, heal_orphaned_reminders, disable_feeds,
               reset_whats_new, force_review_prompt, remove_from_ses_suppression]
    object_actions = [
        (mark_email_verified, 'Mark email verified'),
        (send_password_reset, 'Send password reset'),
        (purge_push_tokens, 'Purge push tokens'),
        (force_logout, 'Force logout'),
        (send_dormant_warning, 'Send dormant warning'),
        (recalculate_all_grades, 'Recalculate all grades'),
        (heal_orphaned_reminders, 'Heal orphaned reminders'),
        (disable_feeds, 'Disable feeds'),
        (reset_whats_new, "Reset What's New"),
        (force_review_prompt, 'Trigger review prompt'),
        (remove_from_ses_suppression, 'Remove from SES suppression'),
    ]
    inlines = [UserOAuthProviderInline, UserPushTokenInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        def _user_count_subquery(model, user_path='user'):
            return Coalesce(Subquery(
                model.objects.filter(**{user_path: OuterRef('pk')})
                .values(user_path)
                .annotate(c=Count('id'))
                .values('c')[:1]
            ), 0)

        return qs.prefetch_related('oauth_providers').annotate(
            _num_notes=_user_count_subquery(Note),
            _num_courses=_user_count_subquery(Course, 'course_group__user'),
            _num_homework=_user_count_subquery(Homework, 'course__course_group__user'),
            _num_events=_user_count_subquery(Event),
            _num_attachments=_user_count_subquery(Attachment),
            _num_external_calendars=_user_count_subquery(ExternalCalendar),
        )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            base = self.readonly_fields + ('created_at', 'last_login', 'last_login_legacy', 'last_activity',
                                           'mobile_app_usage_percent_30d', 'is_power_user', 'deletion_warning_count',
                                           'deletion_warning_sent_at', 'onboarding_completed_at',
                                           'deletion_requested_at', 'get_2fa_enabled',
                                           'verification_code', 'email_changing',)
            # While a user is pending async cascade-delete, freeze all admin-editable fields
            # to prevent a staff edit from racing with the Celery delete task.
            if obj.deletion_requested_at is not None:
                return base + tuple(f.name for f in obj._meta.fields if f.name not in base)
            return base

        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.deletion_requested_at is not None:
            # Block deletion while the Celery task may still be in flight; allow it once stuck.
            if timezone.now() - obj.deletion_requested_at < timedelta(minutes=10):
                return False
        return super().has_delete_permission(request, obj)

    def get_deleted_objects(self, objs, request):
        deleted_objects, model_count, perms_needed, protected = super().get_deleted_objects(objs, request)
        perms_needed.discard('user settings')
        perms_needed.discard('user profile')
        perms_needed.discard('user client activity')
        perms_needed.discard('log entry')
        return deleted_objects, model_count, perms_needed, protected

    def get_2fa_enabled(self, obj):
        return TOTPDevice.objects.filter(user=obj, confirmed=True).exists()

    get_2fa_enabled.short_description = '2FA'
    get_2fa_enabled.boolean = True

    def get_auth_type(self, obj):
        auth_types = []
        if obj.has_usable_password():
            auth_types.append('Password')

        for provider in obj.oauth_providers.all():
            auth_types.append(provider.get_provider_display())

        return ', '.join(auth_types) if auth_types else 'None'

    get_auth_type.short_description = 'Auth Type'

    def num_notes(self, obj):
        return obj._num_notes

    num_notes.short_description = 'Notes'
    num_notes.admin_order_field = '_num_notes'

    def num_courses(self, obj):
        return obj._num_courses

    num_courses.short_description = 'Classes'
    num_courses.admin_order_field = '_num_courses'

    def num_homework(self, obj):
        return obj._num_homework

    num_homework.short_description = 'Assignments'
    num_homework.admin_order_field = '_num_homework'

    def num_events(self, obj):
        return obj._num_events

    num_events.short_description = 'Events'
    num_events.admin_order_field = '_num_events'

    def num_attachments(self, obj):
        return obj._num_attachments

    num_attachments.short_description = 'Attachments'
    num_attachments.admin_order_field = '_num_attachments'

    def num_external_calendars(self, obj):
        return obj._num_external_calendars

    num_external_calendars.short_description = 'Ext Calendars'
    num_external_calendars.admin_order_field = '_num_external_calendars'


class UserProfileAdmin(BaseModelAdmin):
    list_display = ['get_user', 'phone', 'phone_verified', 'get_last_login', 'get_last_activity']
    list_filter = [staff_filter('user')]
    search_fields = ('user__id', 'user__email', 'user__username')
    ordering = ('-user__last_activity',)
    readonly_fields = ('user', 'phone_changing', 'phone_verification_code', 'phone_verified',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_user(self, obj):
        if obj.user:
            return obj.user.get_username()
        else:
            return ''

    def get_last_login(self, obj):
        if obj.user:
            return obj.user.last_login
        else:
            return ''

    def get_last_activity(self, obj):
        if obj.user:
            return obj.user.last_activity
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'
    get_last_login.short_description = 'Last Login'
    get_last_login.admin_order_field = 'user__last_login'


class UserSettingsAdmin(BaseModelAdmin):
    list_display = ['get_user', 'time_zone', 'default_view', 'default_reminder_type', 'color_scheme_theme',
                    'review_prompts_requested', 'get_last_activity']
    list_filter = ['default_view', 'week_starts_on', 'remember_filter_state', 'calendar_event_limit',
                   'calendar_use_category_colors', 'default_reminder_type', 'color_scheme_theme',
                   prompt_for_review_filter('prompt_for_review'),
                   review_prompts_requested_filter('review_prompts_requested'), staff_filter('user')]
    search_fields = ('user__id', 'user__email', 'user__username')
    ordering = ('-user__last_activity',)
    readonly_fields = ('user', 'is_setup_complete', 'next_review_prompt_date', 'review_prompts_requested', 'last_deletion_at',)

    def get_user(self, obj):
        if obj.user:
            return obj.user.get_username()
        else:
            return ''

    def get_last_activity(self, obj):
        if obj.user:
            return obj.user.last_activity
        else:
            return ''

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'
    get_last_activity.short_description = 'Last Activity'
    get_last_activity.admin_order_field = 'user__last_activity'


class UserPushTokenAdmin(BaseModelAdmin):
    list_display = ['get_user', 'device_id', 'get_last_activity']
    list_filter = [staff_filter('user')]
    search_fields = ('user__id', 'user__email', 'user__username')
    ordering = ('-user__last_activity',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_user(self, obj):
        if obj.get_user():
            return obj.get_user().get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'

    def get_last_activity(self, obj):
        if obj.user:
            return obj.user.last_activity
        else:
            return ''

    get_last_activity.short_description = 'Last Activity'
    get_last_activity.admin_order_field = 'user__last_activity'


class UserOAuthProviderAdmin(BaseModelAdmin):
    list_display = ['get_user', 'provider', 'provider_user_id', 'created_at', 'last_used_at']
    list_filter = ['provider', staff_filter('user')]
    search_fields = ('user__id', 'user__email', 'user__username', 'provider_user_id')
    ordering = ('-last_used_at',)
    readonly_fields = ('user', 'provider', 'provider_user_id', 'created_at', 'last_used_at')

    def get_readonly_fields(self, request, obj=None):
        # Override base to avoid adding 'updated_at' - this model uses 'last_used_at' instead
        return self.readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_user(self, obj):
        if obj.user:
            return obj.user.get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


class HeliumOutstandingTokenAdmin(OutstandingTokenAdmin):
    list_filter = (staff_filter('user'),)

    def has_change_permission(self, request, obj=None):
        return False


class HeliumBlacklistedTokenAdmin(BlacklistedTokenAdmin):
    list_filter = (staff_filter('token__user'),)
    search_fields = ('token__jti', 'token__user__id', 'token__user__email', 'token__user__username')
    ordering = ('-token__user__last_activity',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('token',)

        return readonly_fields + self.readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class UserClientActivityAdmin(django_admin.ModelAdmin):
    list_display = ('get_user', 'date', 'client')
    list_filter = ('client', 'date',
                   prompt_for_review_filter('user__settings__prompt_for_review'),
                   review_prompts_requested_filter('user__settings__review_prompts_requested'),
                   staff_filter('user'))
    search_fields = ('user__id', 'user__email', 'user__username')
    ordering = ('-date',)
    readonly_fields = ('user', 'date', 'client')
    actions = [force_review_prompt_for_activities, force_logout_for_activities]

    def get_user(self, obj):
        return obj.user.email if obj.user else ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__email'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Register the models in the Admin
admin_site.register(get_user_model(), UserAdmin)
admin_site.register(UserProfile, UserProfileAdmin)
admin_site.register(UserSettings, UserSettingsAdmin)
admin_site.register(UserPushToken, UserPushTokenAdmin)
admin_site.register(UserOAuthProvider, UserOAuthProviderAdmin)
admin_site.register(UserClientActivity, UserClientActivityAdmin)
admin_site.register(OutstandingTokenProxy, HeliumOutstandingTokenAdmin)
admin_site.register(BlacklistedTokenProxy, HeliumBlacklistedTokenAdmin)
