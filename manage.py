#!/usr/bin/env python

__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.7.19"

import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
