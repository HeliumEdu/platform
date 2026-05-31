__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import json

from django.conf import settings
from django.contrib.admin import action, SimpleListFilter
from django.db.models import Count, Q, TextField
from django.db.models.functions import Cast, Length
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from helium.common.admin import admin_site, BaseModelAdmin, ObjectActionsMixin, staff_filter, \
    has_course_schedule_filter, has_credits_filter, has_weighted_grading_filter, logged_action
from helium.planner.models import CourseGroup, Course, Category, Attachment, MaterialGroup, Material, Event, Homework, \
    Reminder, CourseSchedule, Note
from helium.common.utils import taskutils
from helium.planner.tasks import recalculate_course_group_grade, recalculate_course_grade, recalculate_category_grade


def _linked_notes(obj):
    notes = obj.notes_set.all()
    if not notes:
        return '-'
    return format_html_join(
        ', ', '<a href="{}">{}</a>',
        ((reverse('admin:planner_note_change', args=[n.pk]), n.title or 'Untitled') for n in notes))


@logged_action
@action(description="Recalculate grades for selected items")
def recalculate_grade(modeladmin, request, queryset):
    model_class = queryset.model

    for model in queryset:
        if model_class.__name__ == "CourseGroup":
            taskutils.safe_apply_async(recalculate_course_group_grade, args=(model.pk,), priority=settings.CELERY_PRIORITY_LOW)
        elif model_class.__name__ == "Course":
            taskutils.safe_apply_async(recalculate_course_grade, args=(model.pk,), priority=settings.CELERY_PRIORITY_LOW)
        elif model_class.__name__ == "Category":
            taskutils.safe_apply_async(recalculate_category_grade, args=(model.pk,), priority=settings.CELERY_PRIORITY_LOW)

    modeladmin.message_user(request,
                            f"Grade recalculated for {queryset.count()} items (this action is recursive to children).")


def planner_entity_type_filter(title, parameter_name):
    """
    Factory returning a SimpleListFilter that splits planner records by their linked entity type
    (course, homework, or event).
    """

    class _Filter(SimpleListFilter):
        def lookups(self, request, model_admin):
            return [('course', 'Course'), ('homework', 'Homework'), ('event', 'Event')]

        def queryset(self, request, queryset):
            if self.value() == 'course':
                return queryset.filter(course__isnull=False)
            if self.value() == 'homework':
                return queryset.filter(homework__isnull=False)
            if self.value() == 'event':
                return queryset.filter(event__isnull=False)
            return queryset

    _Filter.title = title
    _Filter.parameter_name = parameter_name
    return _Filter


class AttachmentAdmin(BaseModelAdmin):
    list_display = ('title', 'get_attachment', 'size', 'updated_at', 'get_user',)
    list_filter = (planner_entity_type_filter('Attachment Type', 'attachment_type'), staff_filter('user'))
    search_fields = ('id', 'user__username', 'user__email', 'title')
    autocomplete_fields = ('user',)
    exclude = ('course', 'event', 'homework')

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('linked_entity', 'user', 'size')

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


class CourseGroupAdmin(ObjectActionsMixin, BaseModelAdmin):
    list_display = ('title', 'shown_on_calendar', 'start_date', 'num_courses', 'num_homework',
                    'num_attachments', 'updated_at', 'get_user',)
    list_filter = ('shown_on_calendar', 'example_schedule', has_course_schedule_filter('courses__schedules'),
                   staff_filter('user'))
    search_fields = ('id', 'user__username', 'user__email', 'title')
    autocomplete_fields = ('user',)
    actions = [recalculate_grade]
    object_actions = [
        (recalculate_grade, 'Recalculate grades'),
    ]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('user', 'overall_grade', 'trend',)

        return readonly_fields + self.readonly_fields

    def num_courses(self, obj):
        return obj.num_courses

    num_courses.short_description = 'Classes'

    def num_homework(self, obj):
        return obj.num_homework

    num_homework.short_description = 'Assignments'

    def num_attachments(self, obj):
        return obj.num_attachments

    num_attachments.short_description = 'Attachments'

    def get_user(self, obj):
        if obj.get_user():
            return obj.get_user().get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


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


class CourseAdmin(ObjectActionsMixin, BaseModelAdmin):
    list_display = ('title', 'get_course_group', 'start_date', 'num_homework', 'num_reminders',
                    'num_attachments', 'updated_at', 'get_user',)
    list_filter = ('is_online', 'course_group__shown_on_calendar', 'course_group__example_schedule',
                   has_course_schedule_filter('schedules'), has_weighted_grading_filter('categories__weight'),
                   has_credits_filter('credits'), HasReminderFilter, HasAttachmentFilter,
                   staff_filter('course_group__user'))
    search_fields = ('id', 'title', 'teacher_email', 'course_group__user__username', 'course_group__user__email')
    autocomplete_fields = ('course_group',)
    actions = [recalculate_grade]
    object_actions = [
        (recalculate_grade, 'Recalculate grades'),
    ]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('course_group', 'current_grade', 'trend',)

        return readonly_fields + self.readonly_fields

    def get_course_group(self, obj):
        return obj.course_group.title

    get_course_group.short_description = 'Class Group'
    get_course_group.admin_order_field = 'course_group__title'

    def num_homework(self, obj):
        return obj.num_homework

    num_homework.short_description = 'Assignments'

    def num_reminders(self, obj):
        return obj.num_reminders

    num_reminders.short_description = 'Reminders'

    def num_attachments(self, obj):
        return obj.num_attachments

    num_attachments.short_description = 'Attachments'

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
                   HasCourseScheduleFilter, staff_filter('course__course_group__user'))
    search_fields = ('id', 'course__course_group__user__username', 'course__course_group__user__email')
    autocomplete_fields = ('course',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('course',)

        return readonly_fields + self.readonly_fields

    def get_course(self, obj):
        return obj.course.title

    get_course.short_description = 'Class'
    get_course.admin_order_field = 'course__title'

    def get_course_group(self, obj):
        return obj.course.course_group.title

    get_course_group.short_description = 'Class group'
    get_course_group.admin_order_field = 'course__course_group__title'

    def get_user(self, obj):
        if obj.get_user():
            return obj.get_user().get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'course_group__user__username'


class CategoryAdmin(ObjectActionsMixin, BaseModelAdmin):
    list_display = ('title', 'get_course_group', 'get_course', 'weight', 'num_homework', 'updated_at', 'get_user',)
    list_filter = ('course__course_group__shown_on_calendar', 'course__course_group__example_schedule',
                   has_weighted_grading_filter('weight'), staff_filter('course__course_group__user'))
    search_fields = ('id', 'title', 'course__course_group__user__username', 'course__course_group__user__email')
    autocomplete_fields = ('course',)
    actions = [recalculate_grade]
    object_actions = [
        (recalculate_grade, 'Recalculate grades'),
    ]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('course', 'average_grade', 'grade_by_weight', 'trend',)

        return readonly_fields + self.readonly_fields

    def get_course(self, obj):
        return obj.course.title

    get_course.short_description = 'Class'
    get_course.admin_order_field = 'course__title'

    def get_course_group(self, obj):
        return obj.course.course_group.title

    get_course_group.short_description = 'Class group'
    get_course_group.admin_order_field = 'course__course_group__title'

    def num_homework(self, obj):
        return obj.num_homework

    num_homework.short_description = 'Assignments'

    def get_user(self, obj):
        return obj.get_user().username

    get_user.short_description = 'User'
    get_user.admin_order_field = 'course__course_group__user__username'


class EventAdmin(BaseModelAdmin):
    list_display = ('title', 'start', 'num_reminders', 'num_attachments', 'updated_at', 'get_user',)
    list_filter = ('all_day', 'example_schedule', HasReminderFilter, HasAttachmentFilter, staff_filter('user'))
    search_fields = ('id', 'title', 'user__username', 'user__email')
    ordering = ('-start',)
    autocomplete_fields = ('user',)
    exclude = ('comments',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('owner_id', 'user', 'linked_notes')

        return readonly_fields + self.readonly_fields

    def linked_notes(self, obj):
        return _linked_notes(obj)

    linked_notes.short_description = 'Notes'

    def num_reminders(self, obj):
        return obj.num_reminders

    num_reminders.short_description = 'Reminders'

    def num_attachments(self, obj):
        return obj.num_attachments

    num_attachments.short_description = 'Attachments'

    def get_user(self, obj):
        return obj.get_user().username

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


class HomeworkAdmin(BaseModelAdmin):
    list_display = ('title', 'get_course_group', 'get_course', 'start', 'num_reminders',
                    'num_attachments', 'completed_at', 'updated_at', 'get_user',)
    list_filter = ('all_day', 'completed', 'course__course_group__shown_on_calendar',
                   'course__course_group__example_schedule',
                   has_weighted_grading_filter('course__categories__weight'), HasReminderFilter, HasAttachmentFilter,
                   staff_filter('course__course_group__user'))
    search_fields = ('id', 'title', 'course__course_group__user__username', 'course__course_group__user__email')
    ordering = ('-start',)
    autocomplete_fields = ('category', 'course')
    exclude = ('comments', 'materials',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('completed_at', 'category', 'course', 'linked_materials', 'linked_notes')

        return readonly_fields + self.readonly_fields

    def linked_materials(self, obj):
        materials = obj.materials.all()
        if not materials:
            return '-'
        return format_html_join(
            ', ', '<a href="{}">{}</a>',
            ((reverse('admin:planner_material_change', args=[m.pk]), m.title) for m in materials))

    linked_materials.short_description = 'Resources'

    def linked_notes(self, obj):
        return _linked_notes(obj)

    linked_notes.short_description = 'Notes'

    def get_course(self, obj):
        return obj.course.title

    get_course.short_description = 'Class'
    get_course.admin_order_field = 'course__title'

    def get_course_group(self, obj):
        return obj.course.course_group.title

    get_course_group.short_description = 'Class group'
    get_course_group.admin_order_field = 'course__course_group__title'

    def num_reminders(self, obj):
        return obj.num_reminders

    num_reminders.short_description = 'Reminders'

    def num_attachments(self, obj):
        return obj.num_attachments

    num_attachments.short_description = 'Attachments'

    def get_user(self, obj):
        return obj.get_user().username

    get_user.short_description = 'User'
    get_user.admin_order_field = 'course__course_group__user__username'


class MaterialGroupAdmin(BaseModelAdmin):
    list_display = ('title', 'shown_on_calendar', 'num_materials', 'updated_at', 'get_user',)
    list_filter = ('shown_on_calendar', 'example_schedule', staff_filter('user'))
    search_fields = ('id', 'title', 'user__username', 'user__email')
    autocomplete_fields = ('user',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('user',)

        return readonly_fields + self.readonly_fields

    def num_materials(self, obj):
        return obj.num_materials

    num_materials.short_description = 'Resources'

    def get_user(self, obj):
        if obj.get_user():
            return obj.get_user().get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'


class MaterialAdmin(BaseModelAdmin):
    list_display = ('title', 'get_material_group', 'status', 'condition', 'updated_at', 'get_user',)
    list_filter = ('material_group__shown_on_calendar', 'material_group__example_schedule',
                   staff_filter('material_group__user'))
    search_fields = ('id', 'title', 'material_group__user__username', 'material_group__user__email')
    autocomplete_fields = ('material_group',)
    exclude = ('details', 'courses',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('material_group', 'linked_courses', 'linked_notes')

        return readonly_fields + self.readonly_fields

    def linked_courses(self, obj):
        courses = obj.courses.all()
        if not courses:
            return '-'
        return format_html_join(
            ', ', '<a href="{}">{}</a>',
            ((reverse('admin:planner_course_change', args=[c.pk]), c.title) for c in courses))

    linked_courses.short_description = 'Classes'

    def linked_notes(self, obj):
        return _linked_notes(obj)

    linked_notes.short_description = 'Notes'

    def get_material_group(self, obj):
        return obj.material_group.title

    get_material_group.short_description = 'Resource group'
    get_material_group.admin_order_field = 'material_group__title'

    def get_user(self, obj):
        if obj.get_user():
            return obj.get_user().get_username()
        else:
            return ''

    get_user.short_description = 'User'
    get_user.admin_order_field = 'material_group__user__username'


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


@logged_action
@action(description='Mark selected reminders as unsent')
def mark_reminders_unsent(modeladmin, request, queryset):
    updated = queryset.update(sent=False, dismissed=False)
    modeladmin.message_user(request, f'{updated} reminder(s) marked as unsent.')


class ReminderAdmin(ObjectActionsMixin, BaseModelAdmin):
    list_display = ('title', 'start_of_range', 'type', 'sent', 'dismissed', 'updated_at', 'get_user',)
    list_filter = ('type', 'sent', 'dismissed', planner_entity_type_filter('Reminder Type', 'reminder_type'),
                   ReminderExampleScheduleFilter, staff_filter('user'))
    search_fields = ('id', 'title', 'user__username', 'user__email')
    ordering = ('-start_of_range',)
    autocomplete_fields = ('user',)
    exclude = ('course', 'event', 'homework')
    actions = [mark_reminders_unsent]
    object_actions = [
        (mark_reminders_unsent, 'Mark as unsent'),
    ]

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            return readonly_fields + self.readonly_fields + ('linked_entity', 'user', 'start_of_range',)

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
    list_filter = (NoteLinkedToFilter, NoteExampleScheduleFilter, staff_filter('user'))
    search_fields = ('id', 'title', 'user__username', 'user__email')
    autocomplete_fields = ('user',)
    exclude = ('homework', 'events', 'resources')

    def get_exclude(self, request, obj=None):
        excluded = super().get_exclude(request, obj) or ()
        if 'prod' in settings.ENVIRONMENT:
            return excluded + ('content',)
        return excluded

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
