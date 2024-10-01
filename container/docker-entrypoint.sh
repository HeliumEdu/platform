#!/bin/bash

/usr/local/venvs/platform/bin/python manage.py collectstatic --noinput
/usr/local/venvs/platform/bin/python manage.py migrate

service supervisor start; apache2ctl -D FOREGROUND
