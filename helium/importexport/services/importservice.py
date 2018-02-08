import json
import logging

from django.db import transaction
from django.http import HttpRequest
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer
from helium.planner.serializers.categoryserializer import CategorySerializer
from helium.planner.serializers.coursegroupserializer import CourseGroupSerializer
from helium.planner.serializers.courseserializer import CourseSerializer
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.serializers.homeworkserializer import HomeworkSerializer
from helium.planner.serializers.materialgroupserializer import MaterialGroupSerializer
from helium.planner.serializers.materialserializer import MaterialSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

logger = logging.getLogger(__name__)


@transaction.atomic
def import_user(request, json_str):
    """
    Parse the given JSON string and import its associated data for the given user. Each model will be imported in a
    schema matching that of the documented APIs.

    :param request: The request performing the import.
    :param json_str: The JSON string that will be parsed and imported for the user.
    """
    try:
        data = json.loads(json_str)
    except ValueError as e:
        raise ValidationError({
            'detail': e
        })

    for external_calendar in data.get('external_calendars', []):
        serializer = ExternalCalendarSerializer(data=external_calendar)

        if serializer.is_valid():
            serializer.save(user=request.user)
        else:
            raise ValidationError({
                'external_calendars': {
                    external_calendar['id']: serializer.errors
                }
            })
    logger.info("Imported {} external calendars.".format(len(data.get("external_calendars", []))))

    course_group_remap = {}
    for course_group in data.get('course_groups', []):
        serializer = CourseGroupSerializer(data=course_group)

        if serializer.is_valid():
            instance = serializer.save(user=request.user)
            course_group_remap[course_group['id']] = instance.pk
        else:
            raise ValidationError({
                'course_groups': {
                    course_group['id']: serializer.errors
                }
            })
    logger.info("Imported {} course groups.".format(len(data.get("course_groups", []))))

    course_remap = {}
    for course in data.get('courses', []):
        course['course_group'] = course_group_remap.get(course['course_group'], None)

        serializer = CourseSerializer(data=course)

        if serializer.is_valid():
            instance = serializer.save(course_group_id=course['course_group'])
            course_remap[course['id']] = instance.pk
        else:
            raise ValidationError({
                'courses': {
                    course['id']: serializer.errors
                }
            })
    logger.info("Imported {} courses.".format(len(data.get("courses", []))))

    category_remap = {}
    for category in data.get('categories', []):
        request.parser_context['kwargs']['course'] = course_remap.get(category['course'], None)

        serializer = CategorySerializer(data=category, context={'request': request})

        if serializer.is_valid():
            instance = serializer.save(course_id=course_remap.get(category['course'], None))
            category_remap[category['id']] = instance.pk
        else:
            raise ValidationError({
                'categories': {
                    category['id']: serializer.errors
                }
            })
    logger.info("Imported {} categories.".format(len(data.get("categories", []))))

    material_group_remap = {}
    for material_group in data.get('material_groups', []):
        serializer = MaterialGroupSerializer(data=material_group)

        if serializer.is_valid():
            instance = serializer.save(user=request.user)
            material_group_remap[material_group['id']] = instance.pk
        else:
            raise ValidationError({
                'material_groups': {
                    material_group['id']: serializer.errors
                }
            })
    logger.info("Imported {} material groups.".format(len(data.get("material_groups", []))))

    material_remap = {}
    for material in data.get('materials', []):
        material['material_group'] = material_group_remap.get(material['material_group'], None)
        for i, course in enumerate(material['courses']):
            material['courses'][i] = course_remap.get(course, None)

        serializer = MaterialSerializer(data=material)

        if serializer.is_valid():
            instance = serializer.save(material_group_id=material['material_group'])
            material_remap[material['id']] = instance.pk
        else:
            raise ValidationError({
                'materials': {
                    material['id']: serializer.errors
                }
            })
    logger.info("Imported {} materials.".format(len(data.get("materials", []))))

    event_remap = {}
    for event in data.get('events', []):
        serializer = EventSerializer(data=event)

        if serializer.is_valid():
            instance = serializer.save(user=request.user)
            event_remap[event['id']] = instance.pk
        else:
            raise ValidationError({
                'events': {
                    event['id']: serializer.errors
                }
            })
    logger.info("Imported {} events.".format(len(data.get("events", []))))

    homework_remap = {}
    for homework in data.get('homework', []):
        homework['course'] = course_remap.get(homework['course'], None)
        homework['category'] = category_remap.get(homework['category'], None) if \
            ('category' in homework and homework['category']) else None
        for i, material in enumerate(homework['materials']):
            homework['materials'][i] = material_remap.get(material, None)

        serializer = HomeworkSerializer(data=homework)

        if serializer.is_valid():
            instance = serializer.save(course_id=homework['course'])
            homework_remap[homework['id']] = instance.pk
        else:
            raise ValidationError({
                'homework': {
                    homework['id']: serializer.errors
                }
            })
    logger.info("Imported {} homework.".format(len(data.get("homework", []))))

    for reminder in data.get('reminders', []):
        reminder['homework'] = homework_remap.get(reminder['homework'], None) if \
            ('homework' in reminder and reminder['homework']) else None
        reminder['event'] = event_remap.get(reminder['event'], None) if \
            ('event' in reminder and reminder['event']) else None

        serializer = ReminderSerializer(data=reminder)

        if serializer.is_valid():
            serializer.save(user=request.user)
        else:
            raise ValidationError({
                'reminders': {
                    reminder['id']: serializer.errors
                }
            })
    logger.info("Imported {} reminders.".format(len(data.get("reminders", []))))


def __adjust_schedule_relative_today(user):
    # TODO: implement adjustmenets to current month
    pass


def import_example_schedule(user):
    request = Request(HttpRequest(), parser_context={'kwargs': {}})
    request.user = user

    # TODO: get a better example schedule
    json_str = '{"external_calendars":[{"id":1,"title":"My Calendar","url":"http://go.com/valid-ical-feed","color":"#fad165","shown_on_calendar":true,"user":1}],"course_groups":[{"id":1,"title":"Test Course Group","start_date":"2017-01-06","end_date":"2017-05-08","shown_on_calendar":true,"average_grade":"66.6667","trend":null,"private_slug":null,"user":1,"num_days":122,"num_days_completed":397,"num_homework":1,"num_homework_completed":1,"num_homework_graded":1},{"id":2,"title":"Test Course Group","start_date":"2017-01-06","end_date":"2017-05-08","shown_on_calendar":true,"average_grade":"-1.0000","trend":null,"private_slug":null,"user":1,"num_days":122,"num_days_completed":397,"num_homework":1,"num_homework_completed":0,"num_homework_graded":0}],"courses":[{"id":1,"title":"Test Course","room":"","credits":"5.00","color":"#4986e7","website":"http://mycourse.com","is_online":false,"current_grade":"66.6667","trend":null,"private_slug":null,"teacher_name":"My Teacher","teacher_email":"teacher@email.com","start_date":"2017-01-06","end_date":"2017-05-08","days_of_week":"0000000","sun_start_time":"12:00:00","sun_end_time":"12:00:00","mon_start_time":"12:00:00","mon_end_time":"12:00:00","tue_start_time":"12:00:00","tue_end_time":"12:00:00","wed_start_time":"12:00:00","wed_end_time":"12:00:00","thu_start_time":"12:00:00","thu_end_time":"12:00:00","fri_start_time":"12:00:00","fri_end_time":"12:00:00","sat_start_time":"12:00:00","sat_end_time":"12:00:00","days_of_week_alt":"0000000","sun_start_time_alt":"12:00:00","sun_end_time_alt":"12:00:00","mon_start_time_alt":"12:00:00","mon_end_time_alt":"12:00:00","tue_start_time_alt":"12:00:00","tue_end_time_alt":"12:00:00","wed_start_time_alt":"12:00:00","wed_end_time_alt":"12:00:00","thu_start_time_alt":"12:00:00","thu_end_time_alt":"12:00:00","fri_start_time_alt":"12:00:00","fri_end_time_alt":"12:00:00","sat_start_time_alt":"12:00:00","sat_end_time_alt":"12:00:00","course_group":1,"num_days":122,"num_days_completed":397,"has_weighted_grading":false,"num_homework":1,"num_homework_completed":1,"num_homework_graded":1},{"id":2,"title":"Test Course","room":"DNC 201","credits":"5.00","color":"#4986e7","website":"http://mycourse.com","is_online":false,"current_grade":"-1.0000","trend":null,"private_slug":null,"teacher_name":"My Teacher","teacher_email":"teacher@email.com","start_date":"2017-01-06","end_date":"2017-05-08","days_of_week":"0000000","sun_start_time":"12:00:00","sun_end_time":"12:00:00","mon_start_time":"12:00:00","mon_end_time":"12:00:00","tue_start_time":"12:00:00","tue_end_time":"12:00:00","wed_start_time":"12:00:00","wed_end_time":"12:00:00","thu_start_time":"12:00:00","thu_end_time":"12:00:00","fri_start_time":"12:00:00","fri_end_time":"12:00:00","sat_start_time":"12:00:00","sat_end_time":"12:00:00","days_of_week_alt":"0000000","sun_start_time_alt":"12:00:00","sun_end_time_alt":"12:00:00","mon_start_time_alt":"12:00:00","mon_end_time_alt":"12:00:00","tue_start_time_alt":"12:00:00","tue_end_time_alt":"12:00:00","wed_start_time_alt":"12:00:00","wed_end_time_alt":"12:00:00","thu_start_time_alt":"12:00:00","thu_end_time_alt":"12:00:00","fri_start_time_alt":"12:00:00","fri_end_time_alt":"12:00:00","sat_start_time_alt":"12:00:00","sat_end_time_alt":"12:00:00","course_group":2,"num_days":122,"num_days_completed":397,"has_weighted_grading":false,"num_homework":1,"num_homework_completed":0,"num_homework_graded":0}],"categories":[{"id":2,"title":"Test Category 1","weight":"0.00","average_grade":"-1.0000","grade_by_weight":"0.0000","trend":null,"color":"#4986e7","course":2,"num_homework":1,"num_homework_graded":0},{"id":1,"title":"Uncategorized","weight":"0.00","average_grade":"66.6667","grade_by_weight":"0.0000","trend":null,"color":"#4986e7","course":1,"num_homework":1,"num_homework_graded":1}],"material_groups":[{"id":1,"title":"Test Material Group","shown_on_calendar":true,"user":1}],"materials":[{"id":1,"title":"Test Material","status":3,"condition":7,"website":"http://www.material.com","price":"9.99","details":"Return by 7/1","material_group":1,"courses":[]}],"events":[{"id":1,"title":"Test Event","all_day":false,"show_end_time":true,"start":"2017-05-08T12:00:00Z","end":"2017-05-08T14:00:00Z","priority":75,"url":null,"comments":"A comment on an event.","attachments":[],"reminders":[],"user":1,"calendar_item_type":0},{"id":2,"title":"Test Event","all_day":false,"show_end_time":true,"start":"2017-05-08T12:00:00Z","end":"2017-05-08T14:00:00Z","priority":75,"url":null,"comments":"A comment on an event.","attachments":[],"reminders":[],"user":1,"calendar_item_type":0}],"homework":[{"id":1,"title":"Test Homework","all_day":false,"show_end_time":true,"start":"2017-05-08T16:00:00Z","end":"2017-05-08T18:00:00Z","priority":65,"url":null,"comments":"A comment on a homework.","current_grade":"20/30","completed":true,"category":1,"materials":[1],"attachments":[],"reminders":[1],"course":1,"calendar_item_type":1},{"id":2,"title":"Test Homework","all_day":false,"show_end_time":true,"start":"2017-05-08T16:00:00Z","end":"2017-05-08T18:00:00Z","priority":65,"url":null,"comments":"A comment on a homework.","current_grade":"-1/100","completed":false,"category":2,"materials":[],"attachments":[],"reminders":[],"course":2,"calendar_item_type":1}],"reminders":[{"id":1,"title":"Test Reminder","message":"You need to do something now.","start_of_range":"2017-05-08T15:45:00Z","offset":15,"offset_type":0,"type":2,"sent":false,"homework":1,"event":null,"user":1}]}'

    import_user(request, json_str)

    __adjust_schedule_relative_today(user)
