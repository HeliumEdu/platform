__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import json
import tempfile
import webbrowser

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = "Preview an email template in the browser with sample context data."

    def add_arguments(self, parser):
        parser.add_argument(
            "template",
            type=str,
            help="Template name without extension (e.g., 'email/inactive_warning')"
        )
        parser.add_argument(
            "--context",
            type=str,
            default="{}",
            help="JSON string of context variables (e.g., '{\"days_remaining\": 7}')"
        )

    def handle(self, *args, **options):
        template_name = options["template"]

        try:
            context = json.loads(options["context"])
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in --context: {e}")

        # Add common context variables that templates typically expect
        default_context = {
            'PROJECT_NAME': settings.PROJECT_NAME,
            'login_url': f"{settings.PROJECT_APP_HOST}/login",
            'support_url': getattr(settings, 'SUPPORT_URL', 'https://support.example.com'),
            'status_url': getattr(settings, 'STATUS_URL', 'https://status.example.com'),
        }
        default_context.update(context)
        context = default_context

        try:
            html_content = render_to_string(f"{template_name}.html", context)
        except TemplateDoesNotExist:
            raise CommandError(f"Template not found: {template_name}.html")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html_content)
            temp_path = f.name

        webbrowser.open(f"file://{temp_path}")
        self.stdout.write(self.style.SUCCESS(f"Opened preview: {temp_path}"))
