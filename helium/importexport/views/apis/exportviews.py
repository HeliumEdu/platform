__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.27"

import logging

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.viewsets import ViewSet

from helium.common.views.views import HeliumAPIView
from helium.feed.models import ExternalCalendar
from helium.importexport.serializers.exportserializer import ExportSerializer
from helium.planner.models import CourseGroup, Course, CourseSchedule, Category, MaterialGroup, Material, Event, \
    Homework, Reminder

logger = logging.getLogger(__name__)


class ExportResourceView(ViewSet, HeliumAPIView):
    queryset = get_user_model().objects.all()
    serializer_class = ExportSerializer
    permission_classes = (IsAuthenticated,)

    def export_data(self, request, *args, **kwargs):
        """
        Return an export of all non-sensitive data for the user. The response will contain a `Content-Disposition` of
        `attachment; filename=Helium_<username>.json`, so if the request is initiated from an HTML form, the response
        will be a downloadable file in a browser.

        The exported data for each model type will match that of the documented APIs.
        """
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

        response = HttpResponse(json_str, content_type='application/json; charset=utf-8')
        response['Filename'] = 'Helium_' + user.username + '.json'
        response['Content-Disposition'] = 'attachment; filename=Helium_' + user.username + '.json'
        return response
