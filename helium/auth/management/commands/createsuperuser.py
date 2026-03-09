__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import getpass
import os
import sys

from django.contrib.auth import get_user_model
from django.contrib.auth.management.commands.createsuperuser import (
    Command as BaseCommand,
    NotRunningInTTYException,
    PASSWORD_FIELD,
)
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from django.core.management.base import CommandError
from django.db import IntegrityError

from helium.auth.utils.userutils import generate_unique_username_from_email


class Command(BaseCommand):
    """
    Override Django's createsuperuser to prompt for email only.
    Username is auto-generated from the email address.
    """

    def handle(self, *args, **options):
        UserModel = get_user_model()
        database = options["database"]
        user_data = {}

        try:
            UserModel._meta.get_field(PASSWORD_FIELD)
        except exceptions.FieldDoesNotExist:
            pass
        else:
            user_data[PASSWORD_FIELD] = None

        try:
            if options["interactive"]:
                if hasattr(self.stdin, "isatty") and not self.stdin.isatty():
                    raise NotRunningInTTYException

                email_field = UserModel._meta.get_field("email")

                while True:
                    # Prompt for email (from REQUIRED_FIELDS)
                    email = options.get("email")
                    while not email:
                        message = self._get_input_message(email_field)
                        email = self.get_input_data(email_field, message)
                        if not email:
                            self.stderr.write("Error: This field cannot be blank.")
                    user_data["email"] = email

                    # Prompt for password
                    fake_user_data = {"email": email}
                    while PASSWORD_FIELD in user_data and user_data[PASSWORD_FIELD] is None:
                        password = getpass.getpass()
                        password2 = getpass.getpass("Password (again): ")
                        if password != password2:
                            self.stderr.write("Error: Your passwords didn't match.")
                            continue
                        if password.strip() == "":
                            self.stderr.write("Error: Blank passwords aren't allowed.")
                            continue
                        try:
                            validate_password(password2, UserModel(**fake_user_data))
                        except exceptions.ValidationError as err:
                            self.stderr.write("\n".join(err.messages))
                            response = input(
                                "Bypass password validation and create user anyway? [y/N]: "
                            )
                            if response.lower() != "y":
                                continue
                        user_data[PASSWORD_FIELD] = password

                    user_data[UserModel.USERNAME_FIELD] = generate_unique_username_from_email(email)

                    try:
                        UserModel._default_manager.db_manager(database).create_superuser(**user_data)
                        break
                    except IntegrityError:
                        self.stderr.write("Error: That email address is already taken.")
                        email = None
                        user_data = {PASSWORD_FIELD: None} if PASSWORD_FIELD in user_data else {}
            else:
                # Non-interactive mode: require --email (or env var), optional --username.
                email = options.get("email") or os.environ.get("DJANGO_SUPERUSER_EMAIL")
                if not email:
                    raise CommandError("You must use --email with --noinput.")
                user_data["email"] = email

                if PASSWORD_FIELD in user_data:
                    user_data[PASSWORD_FIELD] = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

                username = options.get(UserModel.USERNAME_FIELD) or os.environ.get(
                    "DJANGO_SUPERUSER_" + UserModel.USERNAME_FIELD.upper()
                )
                if username:
                    user_data[UserModel.USERNAME_FIELD] = username

                if UserModel.USERNAME_FIELD not in user_data:
                    user_data[UserModel.USERNAME_FIELD] = generate_unique_username_from_email(email)

                try:
                    UserModel._default_manager.db_manager(database).create_superuser(**user_data)
                except IntegrityError:
                    raise CommandError("That email address is already taken.")

            if options["verbosity"] >= 1:
                self.stdout.write("Superuser created successfully.")
        except KeyboardInterrupt:
            self.stderr.write("\nOperation cancelled.")
            sys.exit(1)
        except exceptions.ValidationError as e:
            raise CommandError("; ".join(e.messages))
        except NotRunningInTTYException:
            self.stdout.write(
                "Superuser creation skipped due to not running in a TTY. "
                "You can run `manage.py createsuperuser` in your project "
                "to create one manually."
            )
