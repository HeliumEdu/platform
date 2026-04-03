__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import json

from django.conf import settings
from django.contrib.admin import action, SimpleListFilter
from django.db.models import Count, Q, TextField
from django.db.models.functions import Cast, Length
from django.urls import reverse
from django.utils.html import format_html

from helium.common.admin import admin_site, BaseModelAdmin
from helium.planner.models import CourseGroup, Course, Category, Attachment, MaterialGroup, Material, Event, Homework, \
    Reminder, CourseSchedule, Note
from helium.planner.tasks import recalculate_course_group_grade, recalculate_course_grade, recalculate_category_grade


@action(description="Recalculate grades for selected items")
def recalculate_grade(modeladmin, request, queryset):
    model_class = queryset.model

    for model in queryset:
        if model_class.__name__ == "CourseGroup":
            recalculate_course_group_grade.apply_async(args=(model.pk,), priority=settings.CELERY_PRIORITY_LOW)
        elif model_class.__name__ == "Course":
            recalculate_course_grade.apply_async(args=(model.pk,), priority=settings.CELERY_PRIORITY_LOW)
        elif model_class.__name__ == "Category":
            recalculate_category_grade.apply_async(args=(model.pk,), priority=settings.CELERY_PRIORITY_LOW)

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
    list_display = ('title', 'get_attachment', 'size', 'updated_at', 'get_user',)
    list_filter = (AttachmentType,)
    search_fields = ('id', 'user__username', 'user__email', 'title')
    autocomplete_fields = ('user',)
    exclude = ('course', 'event', 'homework')

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('linked_entity', 'user')

        return readonly_fields + self.readonly_fields

    def get_attachment(self, obj):
        return obj.attachment

    get_attachment.short_description = 'Attachment'
    get_attachment.admin_order_field = 'attachment'

    def get_user(self, obj):
        return obj.get_user().username

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'

    def linked_entity(self, obj):
        if obj.course:
            url = reverse('admin:planner_course_change', args=[obj.course.pk])
            return format_html('<a href="{}">{} (Course)</a>', url, obj.course.title)
        elif obj.event:
            url = reverse('admin:planner_event_change', args=[obj.event.pk])
            return format_html('<a href="{}">{} (Event)</a>', url, obj.event.title)
        elif obj.homework:
            url = reverse('admin:planner_homework_change', args=[obj.homework.pk])
            return format_html('<a href="{}">{} (Homework)</a>', url, obj.homework.title)
        return '-'

    linked_entity.short_description = 'Linked Entity'


class CourseGroupHasCourseScheduleFilter(SimpleListFilter):
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
                Q(courses__schedules__isnull=False) & ~Q(courses__schedules__days_of_week="0000000")).distinct()
        elif self.value() == 'no':
            return queryset.exclude(
                Q(courses__schedules__isnull=False) & ~Q(courses__schedules__days_of_week="0000000")).distinct()
        else:
            return queryset


class CourseGroupAdmin(BaseModelAdmin):
    list_display = ('title', 'shown_on_calendar', 'start_date', 'num_courses', 'num_homework',
                    'num_attachments', 'updated_at', 'get_user',)
    list_filter = ('shown_on_calendar', 'example_schedule', CourseGroupHasCourseScheduleFilter)
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
    title = 'has course schedule'
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
    title = 'has attachments'
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
    title = 'has weighted grading'
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


class CourseHasCreditsFilter(SimpleListFilter):
    title = 'has credits'
    parameter_name = 'has_credits'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(credits__gt=0).distinct()
        elif self.value() == 'no':
            return queryset.filter(credits=0).distinct()
        else:
            return queryset


class HasReminderFilter(SimpleListFilter):
    title = 'has reminders'
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


class CourseAdmin(BaseModelAdmin):
    list_display = ('title', 'get_course_group', 'start_date', 'num_homework', 'num_reminders',
                    'num_attachments', 'updated_at', 'get_user',)
    list_filter = ('is_online', 'course_group__shown_on_calendar', 'course_group__example_schedule',
                   CourseHasCourseScheduleFilter, CourseHasWeightedGradingFilter,
                   CourseHasCreditsFilter, HasReminderFilter, HasAttachmentFilter,)
    search_fields = ('id', 'title', 'teacher_email', 'course_group__user__username', 'course_group__user__email')
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
    title = 'has course schedule'
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
    list_filter = ('course__course_group__shown_on_calendar', 'course__course_group__example_schedule',
                   HasCourseScheduleFilter)
    search_fields = ('id', 'course__course_group__user__username', 'course__course_group__user__email')
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
    title = 'has weighted grading'
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
    list_display = ('title', 'get_course_group', 'get_course', 'weight', 'num_homework', 'updated_at', 'get_user',)
    list_filter = ('course__course_group__shown_on_calendar', 'course__course_group__example_schedule',
                   CategoryHasWeightedGradingFilter)
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


class EventAdmin(BaseModelAdmin):
    list_display = ('title', 'start', 'num_reminders', 'num_attachments', 'updated_at', 'get_user',)
    list_filter = ('all_day', 'example_schedule', HasReminderFilter, HasAttachmentFilter)
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
    title = 'has weighted grading'
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
    list_display = ('title', 'get_course_group', 'get_course', 'start', 'num_reminders',
                    'num_attachments', 'completed_at', 'updated_at', 'get_user',)
    list_filter = ('all_day', 'completed', 'course__course_group__shown_on_calendar',
                   'course__course_group__example_schedule',
                   HomeworkHasWeightedGradingFilter, HasReminderFilter, HasAttachmentFilter)
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
    list_display = ('title', 'shown_on_calendar', 'num_materials', 'updated_at', 'get_user',)
    list_filter = ('shown_on_calendar', 'example_schedule')
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
    list_display = ('title', 'get_material_group', 'status', 'condition', 'updated_at', 'get_user',)
    list_filter = ('status', 'condition', 'material_group__shown_on_calendar', 'material_group__example_schedule')
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


class ReminderType(SimpleListFilter):
    title = 'Reminder Type'
    parameter_name = 'reminder_type'

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


class ReminderExampleScheduleFilter(SimpleListFilter):
    title = 'Example Schedule'
    parameter_name = 'example_schedule'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        example_schedule_q = (
            Q(homework__course__course_group__example_schedule=True) |
            Q(event__example_schedule=True) |
            Q(course__course_group__example_schedule=True)
        )
        if self.value() == 'yes':
            return queryset.filter(example_schedule_q)
        elif self.value() == 'no':
            return queryset.exclude(example_schedule_q)
        return queryset


class ReminderAdmin(BaseModelAdmin):
    list_display = ('title', 'start_of_range', 'type', 'sent', 'dismissed', 'updated_at', 'get_user',)
    list_filter = ('type', 'sent', 'dismissed', ReminderType, ReminderExampleScheduleFilter)
    search_fields = ('id', 'title', 'user__username', 'user__email')
    ordering = ('-start_of_range',)
    autocomplete_fields = ('user',)
    exclude = ('course', 'event', 'homework')

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('linked_entity', 'user')

        return readonly_fields + self.readonly_fields

    def get_user(self, obj):
        return obj.get_user().username

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'

    def linked_entity(self, obj):
        if obj.course:
            url = reverse('admin:planner_course_change', args=[obj.course.pk])
            return format_html('<a href="{}">{} (Course)</a>', url, obj.course.title)
        elif obj.event:
            url = reverse('admin:planner_event_change', args=[obj.event.pk])
            return format_html('<a href="{}">{} (Event)</a>', url, obj.event.title)
        elif obj.homework:
            url = reverse('admin:planner_homework_change', args=[obj.homework.pk])
            return format_html('<a href="{}">{} (Homework)</a>', url, obj.homework.title)
        return '-'

    linked_entity.short_description = 'Linked Entity'


class NoteLinkedToFilter(SimpleListFilter):
    title = 'Linked To'
    parameter_name = 'linked_to'

    def lookups(self, request, model_admin):
        return (
            ('homework', 'Homework'),
            ('event', 'Event'),
            ('resource', 'Resource'),
            ('none', 'Unlinked'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'homework':
            return queryset.filter(homework__isnull=False).distinct()
        elif self.value() == 'event':
            return queryset.filter(events__isnull=False).distinct()
        elif self.value() == 'resource':
            return queryset.filter(resources__isnull=False).distinct()
        elif self.value() == 'none':
            return queryset.filter(homework__isnull=True, events__isnull=True, resources__isnull=True)
        return queryset


class NoteExampleScheduleFilter(SimpleListFilter):
    title = 'Example Schedule'
    parameter_name = 'example_schedule'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        example_schedule_q = (
            Q(example_schedule=True) |
            Q(homework__course__course_group__example_schedule=True) |
            Q(events__example_schedule=True) |
            Q(resources__material_group__example_schedule=True)
        )
        if self.value() == 'yes':
            return queryset.filter(example_schedule_q).distinct()
        elif self.value() == 'no':
            return queryset.exclude(example_schedule_q).distinct()
        return queryset


class NoteAdmin(BaseModelAdmin):
    list_display = ('id', 'title', 'get_content_size', 'updated_at', 'get_user')
    list_filter = (NoteLinkedToFilter, NoteExampleScheduleFilter)
    search_fields = ('id', 'title', 'user__username', 'user__email')
    autocomplete_fields = ('user',)
    exclude = ('homework', 'events', 'resources')

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('linked_entity', 'user')

        return readonly_fields + self.readonly_fields

    def get_user(self, obj):
        return obj.user.username

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            content_size=Length(Cast('content', output_field=TextField()))
        )

    def get_content_size(self, obj):
        if obj.content is None:
            return '-'
        return f'{len(json.dumps(obj.content).encode("utf-8"))} B'

    get_content_size.short_description = 'Content Size'
    get_content_size.admin_order_field = 'content_size'

    def linked_entity(self, obj):
        hw = obj.homework.first()
        if hw:
            url = reverse('admin:planner_homework_change', args=[hw.pk])
            return format_html('<a href="{}">{} (Homework)</a>', url, hw.title)

        event = obj.events.first()
        if event:
            url = reverse('admin:planner_event_change', args=[event.pk])
            return format_html('<a href="{}">{} (Event)</a>', url, event.title)

        resource = obj.resources.first()
        if resource:
            url = reverse('admin:planner_material_change', args=[resource.pk])
            return format_html('<a href="{}">{} (Resource)</a>', url, resource.title)

        return '-'

    linked_entity.short_description = 'Linked Entity'


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
admin_site.register(Note, NoteAdmin)
admin_site.register(Reminder, ReminderAdmin)
