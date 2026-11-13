import json
import os
from urllib.parse import urlencode

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status

from helium.feed.models import ExternalCalendar
from helium.planner.models import CourseGroup, Course, CourseSchedule, Category, ResourceGroup, Resource, Event, \
    Homework, Reminder

_RESOURCES_DIR = os.path.join(os.path.dirname(__file__), '..', 'resources')


def get_export_data(test_case, verify_status=True):
    response = test_case.client.get(reverse('importexport_export'))
    if verify_status:
        test_case.assertEqual(response.status_code, status.HTTP_200_OK)

    return json.loads(response.content.decode('utf-8'))


def given_resource_upload(filename, content_type='application/json'):
    with open(os.path.join(_RESOURCES_DIR, filename), 'rb') as fp:
        return SimpleUploadedFile(filename, fp.read(), content_type=content_type)


def post_import(client, payload, filename='import.json', content_type='application/json', **query):
    upload = SimpleUploadedFile(filename, json.dumps(payload).encode(), content_type=content_type)
    return post_import_upload(client, upload, **query)


def post_import_resource(client, filename, content_type='application/json', **query):
    return post_import_upload(client, given_resource_upload(filename, content_type), **query)


def post_import_upload(client, upload, **query):
    url = reverse('importexport_import')
    if query:
        url = f'{url}?{urlencode(query)}'

    return client.post(url, {'file[]': [upload]})


def verify_nothing_imported(test_case):
    for model in (ExternalCalendar, CourseGroup, Course, CourseSchedule, Category, ResourceGroup, Resource, Event,
                  Homework, Reminder):
        test_case.assertEqual(model.objects.count(), 0)
