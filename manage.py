#!/usr/bin/env python

import os
import sys

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.38"

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
