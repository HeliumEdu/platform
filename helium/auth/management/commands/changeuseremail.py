__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import sys

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from helium.auth.utils.userutils import is_admin_allowed_email


class Command(BaseCommand):
    help = "Change a user's email address, identified by their current email."

    def add_arguments(self, parser):
        parser.add_argument("--current-email", type=str, help="The user's current email address")
        parser.add_argument("--new-email", type=str, help="The new email address to assign")

    def handle(self, *args, **options):
        UserModel = get_user_model()

        try:
            current_email = options.get("current_email")
            while not current_email:
                current_email = input("Current email: ").strip()
                if not current_email:
                    self.stderr.write("Error: This field cannot be blank.")

            try:
                user = UserModel.objects.get(email=current_email)
            except UserModel.DoesNotExist:
                raise CommandError(f"No user found with email '{current_email}'.")

            new_email = options.get("new_email")
            while not new_email:
                new_email = input("New email: ").strip()
                if not new_email:
                    self.stderr.write("Error: This field cannot be blank.")

            if UserModel.objects.filter(email=new_email).exists():
                raise CommandError(f"A user with email '{new_email}' already exists.")

            if user.is_superuser and not is_admin_allowed_email(new_email):
                raise CommandError(f"Admin email must be within an allowed domain ({', '.join(settings.ADMIN_ALLOWED_DOMAINS)}).")

            user.email = new_email
            user.save()

            if options["verbosity"] >= 1:
                self.stdout.write(f"Email updated: '{current_email}' -> '{new_email}'.")
        except KeyboardInterrupt:
            self.stderr.write("\nOperation cancelled.")
            sys.exit(1)
