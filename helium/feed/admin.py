from helium.common.admin import admin_site, BaseModelAdmin
from helium.feed.models import ExternalCalendar

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


class ExternalCalendarAdmin(BaseModelAdmin):
    list_display = ['title', 'url', 'color', 'shown_on_calendar', 'get_user', ]
    list_filter = ['shown_on_calendar']
    ordering = ('user__username',)
    readonly_fields = ('user',)

    def get_user(self, obj):
        if obj.get_user():
            return obj.get_user().get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


# Register the models in the Admin
admin_site.register(ExternalCalendar, ExternalCalendarAdmin)
