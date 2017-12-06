"""
Planner admin site.
"""
from django.contrib.admin import ModelAdmin

from helium.common.admin import admin_site
from helium.planner.models import CourseGroup

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class CourseGroupAdmin(ModelAdmin):
    list_display = ('title', 'created_at', 'updated_at', 'shown_on_calendar', 'get_user',)
    list_filter = ('shown_on_calendar',)
    search_fields = ('user__username',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('user', 'created_at', 'updated_at',)

        return self.readonly_fields

    def get_user(self, obj):
        if obj.user:
            return obj.user.get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


# Register the models in the Admin
admin_site.register(CourseGroup, CourseGroupAdmin)
