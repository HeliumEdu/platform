import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.http import HttpRequest
from rest_framework.request import Request

from helium.importexport.services.importservice import import_user, _adjust_schedule_relative_today
from helium.planner.models import Category
from helium.planner.tasks import recalculate_category_grade


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("user_id", type=int, help="The user ID where the schedule will be imported")
        parser.add_argument("path", type=str, help="The Helium schedule file to import")
        parser.add_argument("--adjust-dates", action="store_true",
                            help="Adjust dates in the imported schedule relative to today (as is done with the example schedule when a new user registers)")

    def handle(self, *args, **options):
        user_id = options['user_id']
        path = options['path']
        adjust_dates = options['adjust_dates']

        user = get_user_model().objects.get(pk=user_id)

        request = Request(HttpRequest(), parser_context={'kwargs': {}})
        request.user = user

        with open(path, 'rb') as file:
            json_str = file.read().decode('utf-8')
            data = json.loads(json_str)

            import_user(request, data)

            if adjust_dates:
                _adjust_schedule_relative_today(user)

            for category in Category.objects.for_user(user.pk).iterator():
                recalculate_category_grade.delay(category.pk)
