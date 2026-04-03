__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django import forms
from django.conf import settings
from django.contrib import admin as django_admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth import admin, password_validation
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core import exceptions
from django.db.models import Count, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework_simplejwt.token_blacklist.admin import OutstandingTokenAdmin, BlacklistedTokenAdmin
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from helium.auth.models import UserProfile
from helium.auth.models import UserSettings
from helium.auth.models.useroauthprovider import UserOAuthProvider
from helium.auth.models.userpushtoken import UserPushToken
from helium.auth.utils.userutils import is_admin_allowed_email
from helium.common.admin import admin_site, BaseModelAdmin
from helium.feed.models.externalcalendar import ExternalCalendar
from helium.planner.models.attachment import Attachment
from helium.planner.models.course import Course
from helium.planner.models.event import Event
from helium.planner.models.homework import Homework
from helium.planner.models.note import Note


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


class HasCreditsFilter(SimpleListFilter):
    title = 'has credits'
    parameter_name = 'has_credits'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(course_groups__courses__credits__gt=0).distinct()
        elif self.value() == 'no':
            return queryset.filter(course_groups__courses__credits=0).distinct()
        else:
            return queryset


class HasWeightedGradingFilter(SimpleListFilter):
    title = 'has weighted grading'
    parameter_name = 'has_weighted_grading'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(course_groups__courses__categories__weight__gt=0).distinct()
        elif self.value() == 'no':
            return queryset.filter(course_groups__courses__categories__weight=0).distinct()
        else:
            return queryset


class HasCourseScheduleFilter(SimpleListFilter):
    title = 'has course schedule'
    parameter_name = 'has_course_schedule'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(
                Q(course_groups__courses__schedules__isnull=False) & ~Q(
                    course_groups__courses__schedules__days_of_week="0000000")).distinct()
        elif self.value() == 'no':
            return queryset.exclude(
                Q(course_groups__courses__schedules__isnull=False) & ~Q(
                    course_groups__courses__schedules__days_of_week="0000000")).distinct()
        else:
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


class UserOAuthProviderInline(django_admin.TabularInline):
    model = UserOAuthProvider
    extra = 0
    can_delete = True
    fields = ('provider', 'provider_user_id', 'created_at', 'last_used_at')
    readonly_fields = ('provider', 'provider_user_id', 'created_at', 'last_used_at')

    def has_add_permission(self, request, obj=None):
        return False


class UserAdmin(admin.UserAdmin, BaseModelAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm

    list_display = ('email', 'last_activity', 'get_auth_type',
                    'num_notes', 'num_courses', 'num_homework', 'num_events',
                    'num_attachments', 'num_external_calendars', 'last_login_legacy',
                    'deletion_warning_count', 'created_at', 'is_active')
    list_filter = (ActiveStatusFilter, 'profile__phone_verified', 'settings__default_view',
                   'settings__remember_filter_state', 'settings__calendar_event_limit',
                   'settings__default_reminder_type', 'settings__color_scheme_theme',
                   'settings__calendar_use_category_colors', OAuthProviderFilter, HasWeightedGradingFilter,
                   HasCreditsFilter, HasCourseScheduleFilter)
    search_fields = ('id', 'email', 'username')
    ordering = ('-last_activity',)
    add_fieldsets = (
        (None, {
            'fields': ('username', 'email', 'password1', 'password2',),
        }),
    )
    fieldsets = None
    filter_horizontal = ()
    inlines = [UserOAuthProviderInline]

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
            return self.readonly_fields + ('created_at', 'last_login', 'last_login_legacy', 'last_activity',
                                           'deletion_warning_count', 'deletion_warning_sent_at', 'get_2fa_enabled',)

        return self.readonly_fields

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

    num_courses.short_description = 'Courses'
    num_courses.admin_order_field = '_num_courses'

    def num_homework(self, obj):
        return obj._num_homework

    num_homework.short_description = 'Homework'
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
    search_fields = ('user__id', 'user__email', 'user__username')
    ordering = ('-user__last_activity',)
    readonly_fields = ('user',)

    def has_add_permission(self, request):
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
    list_display = ['get_user', 'time_zone', 'default_view', 'default_reminder_type', 'review_prompts_shown',
                    'get_last_activity']
    list_filter = ['default_view', 'week_starts_on', 'remember_filter_state', 'calendar_event_limit',
                   'calendar_use_category_colors', 'default_reminder_type']
    search_fields = ('user__id', 'user__email', 'user__username')
    ordering = ('-user__last_activity',)
    readonly_fields = ('user',)

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

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'
    get_last_activity.short_description = 'Last Activity'
    get_last_activity.admin_order_field = 'user__last_activity'


class UserPushTokenAdmin(BaseModelAdmin):
    list_display = ['get_user', 'device_id', 'token', 'get_last_activity']
    search_fields = ('user__id', 'user__email', 'user__username')
    ordering = ('-user__last_activity',)
    autocomplete_fields = ('user',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('user',)

        return readonly_fields + self.readonly_fields

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
    list_filter = ['provider']
    search_fields = ('user__id', 'user__email', 'user__username', 'provider_user_id')
    ordering = ('-last_used_at',)
    readonly_fields = ('user', 'provider', 'provider_user_id', 'created_at', 'last_used_at')

    def get_readonly_fields(self, request, obj=None):
        # Override base to avoid adding 'updated_at' - this model uses 'last_used_at' instead
        return self.readonly_fields

    def has_add_permission(self, request):
        return False

    def get_user(self, obj):
        if obj.user:
            return obj.user.get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


class HeliumBlacklistedTokenAdmin(BlacklistedTokenAdmin):
    search_fields = ('token__jti', 'tokne__user__id', 'token__user__email', 'token__user__username')
    ordering = ('-token__user__last_activity',)
    autocomplete_fields = ('token',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('token',)

        return readonly_fields + self.readonly_fields


# Register the models in the Admin
admin_site.register(get_user_model(), UserAdmin)
admin_site.register(UserProfile, UserProfileAdmin)
admin_site.register(UserSettings, UserSettingsAdmin)
admin_site.register(UserPushToken, UserPushTokenAdmin)
admin_site.register(UserOAuthProvider, UserOAuthProviderAdmin)
admin_site.register(OutstandingToken, OutstandingTokenAdmin)
admin_site.register(BlacklistedToken, HeliumBlacklistedTokenAdmin)
