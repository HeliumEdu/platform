from django.conf import settings
from django.contrib import admin as django_admin
from django.contrib.admin import SimpleListFilter
from django.utils import timezone

from helium.common.admin import admin_site, BaseModelAdmin, ObjectActionsMixin, staff_filter, logged_action
from helium.common.utils import taskutils
from helium.feed.models import ExternalCalendar
from helium.feed.services import icalexternalcalendarservice
from helium.feed.tasks import reindex_external_calendars


@logged_action
@django_admin.action(description='Force re-index selected calendars')
def force_reindex_calendars(modeladmin, request, queryset):
    queryset.update(etag=None, last_modified_header=None)
    calendar_ids = list(queryset.values_list('id', flat=True))
    for calendar_id in calendar_ids:
        taskutils.safe_apply_async(reindex_external_calendars,
            kwargs={'calendar_id': calendar_id},
            priority=settings.CELERY_PRIORITY_LOW,
        )
    modeladmin.message_user(request, f'Re-index queued for {len(calendar_ids)} calendar(s).')


@logged_action
@django_admin.action(description='Re-show selected calendars')
def reshow_calendars(modeladmin, request, queryset):
    hidden = list(queryset.filter(shown_on_calendar=False))
    for external_calendar in hidden:
        icalexternalcalendarservice.invalidate_calendar_cache(external_calendar)
    ExternalCalendar.objects.filter(pk__in=[external_calendar.pk for external_calendar in hidden]).update(
        shown_on_calendar=True, updated_at=timezone.now())
    modeladmin.message_user(request, f'Re-shown {len(hidden)} calendar(s).')


class HiddenAfterFailuresFilter(SimpleListFilter):
    title = 'hidden after failures'
    parameter_name = 'hidden_after_failures'

    def lookups(self, request, model_admin):
        return [('yes', 'Yes')]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(shown_on_calendar=False,
                                   consecutive_failures__gte=settings.EXTERNAL_CALENDAR_CONSECUTIVE_FAILURE_THRESHOLD)
        return queryset


class ExternalCalendarAdmin(ObjectActionsMixin, BaseModelAdmin):
    list_display = ['title', 'url', 'shown_on_calendar', 'last_index', 'last_sync_error', 'get_user']
    list_filter = ['shown_on_calendar', HiddenAfterFailuresFilter, 'example_schedule', staff_filter('user')]
    search_fields = ('id', 'title', 'url', 'user__username', 'user__email')
    ordering = ('user__username',)
    autocomplete_fields = ('user',)
    actions = [force_reindex_calendars, reshow_calendars]
    object_actions = [
        (force_reindex_calendars, 'Force re-index'),
        (reshow_calendars, 'Re-show'),
    ]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('user', 'etag', 'last_modified_header',
                                                                'last_index', 'last_sync_error',
                                                                'consecutive_failures',)

        return readonly_fields + self.readonly_fields

    def get_user(self, obj):
        if obj.get_user():
            return obj.get_user().get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


# Register the models in the Admin
admin_site.register(ExternalCalendar, ExternalCalendarAdmin)
