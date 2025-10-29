__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.15.16"

from django.contrib.admin import action, SimpleListFilter
from django.db.models import Count, Q

from helium.common.admin import admin_site, BaseModelAdmin
from helium.planner.models import CourseGroup, Course, Category, Attachment, MaterialGroup, Material, Event, Homework, \
    Reminder, CourseSchedule
from helium.planner.tasks import recalculate_course_group_grade, recalculate_course_grade, recalculate_category_grade


@action(description="Recalculate grades for selected items")
def recalculate_grade(modeladmin, request, queryset):
    model_class = queryset.model

    for course_group in queryset:
        if model_class.__name__ == "CourseGroup":
            recalculate_course_group_grade.delay(course_group.pk)
        elif model_class.__name__ == "Course":
            recalculate_course_grade.delay(course_group.pk)
        elif model_class.__name__ == "Category":
            recalculate_category_grade.delay(course_group.pk)

    modeladmin.message_user(request,
                            f"Grade recalculated for {queryset.count()} items (this action is recursive to children).")


class AttachmentType(SimpleListFilter):
    title = 'Attachment Type'
    parameter_name = 'attachment_type'

    def lookups(self, request, model_admin):
        return (
            ('course', 'Course'),
            ('homework', 'Homework'),
            ('event', 'Event'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'course':
            return queryset.filter(course__isnull=False)
        elif self.value() == 'homework':
            return queryset.filter(homework__isnull=False)
        elif self.value() == 'event':
            return queryset.filter(event__isnull=False)
        else:
            return queryset


class AttachmentAdmin(BaseModelAdmin):
    list_display = ('title', 'get_attachment', 'size', 'created_at', 'updated_at', 'get_user',)
    list_filter = (AttachmentType,)
    search_fields = ('id', 'user__username', 'user__email', 'title')
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


class CourseGroupHasCourseScheduleFilter(SimpleListFilter):
    title = 'Has Course Schedule'
    parameter_name = 'has_course_schedule'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(
                Q(courses__schedules__isnull=False) & ~Q(courses__schedules__days_of_week="0000000")).distinct()
        elif self.value() == 'no':
            return queryset.exclude(
                Q(courses__schedules__isnull=False) & ~Q(courses__schedules__days_of_week="0000000")).distinct()
        else:
            return queryset


class CourseGroupAdmin(BaseModelAdmin):
    list_display = ('title', 'updated_at', 'start_date', 'shown_on_calendar', 'num_courses', 'num_homework',
                    'num_attachments', 'get_user',)
    list_filter = ('shown_on_calendar', CourseGroupHasCourseScheduleFilter)
    search_fields = ('id', 'user__username', 'user__email', 'title')
    autocomplete_fields = ('user',)
    actions = [recalculate_grade]

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


class CourseHasCourseScheduleFilter(SimpleListFilter):
    title = 'Has Course Schedule'
    parameter_name = 'has_course_schedule'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(Q(schedules__isnull=False) & ~Q(schedules__days_of_week="0000000")).distinct()
        elif self.value() == 'no':
            return queryset.exclude(Q(schedules__isnull=False) & ~Q(schedules__days_of_week="0000000")).distinct()
        else:
            return queryset


class HasAttachmentFilter(SimpleListFilter):
    title = 'Has Attachments'
    parameter_name = 'has_attachments'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.annotate(attachments_count=Count('attachments')).filter(attachments_count__gt=0).distinct()
        elif self.value() == 'no':
            return queryset.annotate(attachments_count=Count('attachments')).filter(attachments_count=0).distinct()
        else:
            return queryset


class CourseHasWeightedGradingFilter(SimpleListFilter):
    title = 'Has Weighted Grading'
    parameter_name = 'has_weighted_grading'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(categories__weight__gt=0).distinct()
        elif self.value() == 'no':
            return queryset.filter(categories__weight=0).distinct()
        else:
            return queryset


class CourseAdmin(BaseModelAdmin):
    list_display = ('title', 'updated_at', 'get_course_group', 'start_date', 'num_homework', 'num_attachments',
                    'get_user',)
    list_filter = ('course_group__shown_on_calendar', CourseHasCourseScheduleFilter, CourseHasWeightedGradingFilter,
                   HasAttachmentFilter,)
    search_fields = ('id', 'title', 'course_group__user__username', 'course_group__user__email')
    autocomplete_fields = ('course_group',)
    actions = [recalculate_grade]

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


class HasCourseScheduleFilter(SimpleListFilter):
    title = 'Has Course Schedule'
    parameter_name = 'has_course_schedule'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(days_of_week="0000000").distinct()
        elif self.value() == 'no':
            return queryset.filter(days_of_week="0000000").distinct()
        else:
            return queryset


class CourseScheduleAdmin(BaseModelAdmin):
    list_display = ('days_of_week', 'get_course', 'get_course_group', 'updated_at', 'get_user')
    list_filter = ('course__course_group__shown_on_calendar', HasCourseScheduleFilter)
    search_fields = ('id', 'title', 'course__course_group__user__username', 'course__course_group__user__email')
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
        if obj.get_user():
            return obj.get_user().get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'course_group__user__username'


class CategoryHasWeightedGradingFilter(SimpleListFilter):
    title = 'Has Weighted Grading'
    parameter_name = 'has_weighted_grading'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(weight__gt=0).distinct()
        elif self.value() == 'no':
            return queryset.filter(weight=0).distinct()
        else:
            return queryset


class CategoryAdmin(BaseModelAdmin):
    list_display = ('title', 'get_course_group', 'get_course', 'updated_at', 'weight', 'num_homework', 'get_user',)
    list_filter = ('course__course_group__shown_on_calendar', CategoryHasWeightedGradingFilter)
    search_fields = ('id', 'title', 'course__course_group__user__username', 'course__course_group__user__email')
    autocomplete_fields = ('course',)
    actions = [recalculate_grade]

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


class HasReminderFilter(SimpleListFilter):
    title = 'Has Reminders'
    parameter_name = 'has_reminders'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.annotate(reminders_count=Count('reminders')).filter(reminders_count__gt=0).distinct()
        elif self.value() == 'no':
            return queryset.annotate(reminders_count=Count('reminders')).filter(reminders_count=0).distinct()
        else:
            return queryset


class EventAdmin(BaseModelAdmin):
    list_display = ('title', 'start', 'updated_at', 'num_reminders', 'num_attachments', 'get_user',)
    list_filter = (HasReminderFilter, HasAttachmentFilter)
    search_fields = ('id', 'title', 'user__username', 'user__email')
    ordering = ('-start',)
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


class HomeworkHasWeightedGradingFilter(SimpleListFilter):
    title = 'Has Weighted Grading'
    parameter_name = 'has_weighted_grading'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(course__categories__weight__gt=0).distinct()
        elif self.value() == 'no':
            return queryset.filter(course__categories__weight=0).distinct()
        else:
            return queryset


class HomeworkAdmin(BaseModelAdmin):
    list_display = ('title', 'get_course_group', 'get_course', 'start', 'updated_at', 'num_reminders',
                    'num_attachments', 'get_user',)
    list_filter = ('completed', 'course__course_group__shown_on_calendar', HomeworkHasWeightedGradingFilter,
                   HasReminderFilter, HasAttachmentFilter)
    search_fields = ('id', 'title', 'course__course_group__user__username', 'course__course_group__user__email')
    ordering = ('-start',)
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
    list_display = ('title', 'updated_at', 'shown_on_calendar', 'num_materials', 'get_user',)
    list_filter = ('shown_on_calendar',)
    search_fields = ('id', 'title', 'user__username', 'user__email')
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
    list_display = ('title', 'get_material_group', 'updated_at', 'get_user',)
    list_filter = ('material_group__shown_on_calendar',)
    search_fields = ('id', 'title', 'material_group__user__username', 'material_group__user__email')
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
    list_display = ('title', 'start_of_range', 'updated_at', 'type', 'get_user',)
    list_filter = ('type', 'sent')
    search_fields = ('id', 'title', 'user__username', 'user__email')
    ordering = ('-start_of_range',)
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
admin_site.register(CourseSchedule, CourseScheduleAdmin)
admin_site.register(Category, CategoryAdmin)
admin_site.register(Event, EventAdmin)
admin_site.register(Homework, HomeworkAdmin)
admin_site.register(MaterialGroup, MaterialGroupAdmin)
admin_site.register(Material, MaterialAdmin)
admin_site.register(Reminder, ReminderAdmin)
