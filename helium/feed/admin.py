__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.conf import settings
from django.contrib import admin as django_admin

from helium.common.admin import admin_site, BaseModelAdmin
from helium.feed.models import ExternalCalendar
from helium.feed.tasks import reindex_feeds


@django_admin.action(description='Force re-index selected calendars')
def force_reindex_calendars(modeladmin, request, queryset):
    queryset.update(etag=None, last_modified_header=None)
    calendar_ids = list(queryset.values_list('id', flat=True))
    reindex_feeds.apply_async(
        kwargs={'calendar_ids': calendar_ids},
        priority=settings.CELERY_PRIORITY_LOW,
    )
    modeladmin.message_user(request, f'Re-index queued for {len(calendar_ids)} calendar(s).')


class ExternalCalendarAdmin(BaseModelAdmin):
    list_display = ['title', 'url', 'shown_on_calendar', 'last_index', 'last_sync_error', 'get_user']
    list_filter = ['shown_on_calendar', 'example_schedule']
    search_fields = ('id', 'title', 'url', 'user__username', 'user__email')
    ordering = ('user__username',)
    autocomplete_fields = ('user',)
    actions = [force_reindex_calendars]

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


# Register the models in the Admin
admin_site.register(ExternalCalendar, ExternalCalendarAdmin)
