"""
Planner admin site.
"""
from django.contrib.admin import ModelAdmin

from helium.common.admin import admin_site
from helium.planner.models import CourseGroup, Course
from helium.planner.models.category import Category

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class CourseGroupAdmin(ModelAdmin):
    list_display = ('title', 'created_at', 'updated_at', 'shown_on_calendar', 'get_user',)
    list_filter = ('shown_on_calendar',)
    search_fields = ('title', 'user__username',)
    ordering = ('-updated_at',)

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


class CourseAdmin(ModelAdmin):
    list_display = ('title', 'get_course_group', 'created_at', 'updated_at', 'get_user',)
    search_fields = ('title', 'course_group__user__username',)
    ordering = ('-updated_at',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('created_at', 'updated_at',)

        return self.readonly_fields

    def get_course_group(self, obj):
        return obj.course_group.title

    get_course_group.short_description = 'Course Group'
    get_course_group.admin_order_field = 'course_group__title'

    def get_user(self, obj):
        if obj.get_user():
            return obj.get_user().get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'course_group__user__username'


class CategoryAdmin(ModelAdmin):
    list_display = ('title', 'get_course_group', 'get_course', 'created_at', 'updated_at', 'get_user',)
    search_fields = ('title', 'course__course_group__user__username',)
    ordering = ('-updated_at',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('created_at', 'updated_at',)

        return self.readonly_fields

    def get_course(self, obj):
        return obj.course.title

    get_course.short_description = 'Course'
    get_course.admin_order_field = 'course__title'

    def get_course_group(self, obj):
        return obj.course.course_group.title

    get_course_group.short_description = 'Course group'
    get_course_group.admin_order_field = 'course__course_group__title'

    def get_user(self, obj):
        return obj.get_user().username

    get_user.short_description = 'User'
    get_user.admin_order_field = 'course__course_group__user__username'


# Register the models in the Admin
admin_site.register(CourseGroup, CourseGroupAdmin)
admin_site.register(Course, CourseAdmin)
admin_site.register(Category, CategoryAdmin)
