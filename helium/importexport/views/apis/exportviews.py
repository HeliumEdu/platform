import logging

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

from helium.common.utils import metricutils
from helium.feed.models import ExternalCalendar
from helium.importexport.serializers.exportserializer import ExportSerializer
from helium.planner.models import CourseGroup, Course, CourseSchedule, Category, MaterialGroup, Material, Event, \
    Homework, Reminder

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.7'

logger = logging.getLogger(__name__)


class ExportView(APIView):
    """
    get:
    Return a JSON of all non-sensitive data for the user. The result will be a downloadable file.

    The exported data for each model type will match that of the documented APIs.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = self.request.user

        serializer = ExportSerializer({
            'external_calendars': ExternalCalendar.objects.for_user(user.pk),
            'course_groups': CourseGroup.objects.for_user(user.pk),
            'courses': Course.objects.for_user(user.pk),
            'course_schedules': CourseSchedule.objects.for_user(user.pk),
            'categories': Category.objects.for_user(user.pk),
            'material_groups': MaterialGroup.objects.for_user(user.pk),
            'materials': Material.objects.for_user(user.pk),
            'events': Event.objects.for_user(user.pk),
            'homework': Homework.objects.for_user(user.pk),
            'reminders': Reminder.objects.for_user(user.pk)
        })

        json_str = JSONRenderer().render(serializer.data)

        metricutils.increment('action.user.exported', request)

        response = HttpResponse(json_str, content_type='application/json; charset=utf-8')
        response['Filename'] = 'Helium_' + user.username + '.json'
        response['Content-Disposition'] = 'attachment; filename=Helium_' + user.username + '.json'
        return response
