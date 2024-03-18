__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.6.0"

from helium.common.admin import admin_site, BaseModelAdmin
from helium.planner.models import CourseGroup, Course, Category, Attachment, MaterialGroup, Material, Event, Homework, \
    Reminder


class AttachmentAdmin(BaseModelAdmin):
    list_display = ('title', 'get_attachment', 'size', 'created_at', 'updated_at', 'get_user',)
    search_fields = ('user__username',)
    autocomplete_fields = ('course', 'event', 'homework', 'user')

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('course', 'event', 'homework', 'user')

        return readonly_fields + self.readonly_fields

    def get_attachment(self, obj):
        return obj.attachment

    get_attachment.short_description = 'Attachment'
    get_attachment.admin_order_field = 'attachment'

    def get_user(self, obj):
        return obj.get_user().username

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


class CourseGroupAdmin(BaseModelAdmin):
    list_display = ('title', 'created_at', 'start_date', 'end_date', 'shown_on_calendar', 'get_user',)
    list_filter = ('shown_on_calendar',)
    search_fields = ('title', 'user__username',)
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


class CourseAdmin(BaseModelAdmin):
    list_display = ('title', 'get_course_group', 'created_at', 'start_date', 'end_date', 'get_user',)
    search_fields = ('title', 'course_group__user__username',)
    autocomplete_fields = ('course_group',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('course_group',)

        return readonly_fields + self.readonly_fields

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


class CategoryAdmin(BaseModelAdmin):
    list_display = ('title', 'get_course_group', 'get_course', 'created_at', 'updated_at', 'weight', 'get_user',)
    search_fields = ('title', 'course__course_group__user__username',)
    autocomplete_fields = ('course',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('course',)

        return readonly_fields + self.readonly_fields

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


class EventAdmin(BaseModelAdmin):
    list_display = ('title', 'created_at', 'start', 'end', 'get_user',)
    search_fields = ('title', 'user__username',)
    autocomplete_fields = ('user',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('user',)

        return readonly_fields + self.readonly_fields

    def get_user(self, obj):
        return obj.get_user().username

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


class HomeworkAdmin(BaseModelAdmin):
    list_display = ('title', 'get_course_group', 'get_course', 'created_at', 'start', 'end', 'get_user',)
    search_fields = ('title', 'course__course_group__user__username',)
    autocomplete_fields = ('category', 'materials', 'course')

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('category', 'materials', 'course')

        return readonly_fields + self.readonly_fields

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


class MaterialGroupAdmin(BaseModelAdmin):
    list_display = ('title', 'created_at', 'updated_at', 'shown_on_calendar', 'get_user',)
    list_filter = ('shown_on_calendar',)
    search_fields = ('title', 'user__username',)
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


class MaterialAdmin(BaseModelAdmin):
    list_display = ('title', 'get_material_group', 'created_at', 'updated_at', 'get_user',)
    search_fields = ('title', 'material_group__user__username',)
    autocomplete_fields = ('material_group', 'courses',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('material_group', 'courses')

        return readonly_fields + self.readonly_fields

    def get_material_group(self, obj):
        return obj.material_group.title

    get_material_group.short_description = 'Material Group'
    get_material_group.admin_order_field = 'material_group__title'

    def get_user(self, obj):
        if obj.get_user():
            return obj.get_user().get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'material_group__user__username'


class ReminderAdmin(BaseModelAdmin):
    list_display = ('title', 'created_at', 'updated_at', 'get_user',)
    search_fields = ('title', 'user__username',)
    autocomplete_fields = ('event', 'homework', 'user')

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('event', 'homework', 'user')

        return readonly_fields + self.readonly_fields

    def get_user(self, obj):
        return obj.get_user().username

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


# Register the models in the Admin
admin_site.register(Attachment, AttachmentAdmin)
admin_site.register(CourseGroup, CourseGroupAdmin)
admin_site.register(Course, CourseAdmin)
admin_site.register(Category, CategoryAdmin)
admin_site.register(Event, EventAdmin)
admin_site.register(Homework, HomeworkAdmin)
admin_site.register(MaterialGroup, MaterialGroupAdmin)
admin_site.register(Material, MaterialAdmin)
admin_site.register(Reminder, ReminderAdmin)
