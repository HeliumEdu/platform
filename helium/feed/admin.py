__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

from helium.common.admin import admin_site, BaseModelAdmin
from helium.feed.models import ExternalCalendar


class ExternalCalendarAdmin(BaseModelAdmin):
    list_display = ['title', 'url', 'color', 'shown_on_calendar', 'get_user', ]
    list_filter = ['shown_on_calendar']
    ordering = ('user__username',)
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


# Register the models in the Admin
admin_site.register(ExternalCalendar, ExternalCalendarAdmin)
