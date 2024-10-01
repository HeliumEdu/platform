#!/bin/bash

/usr/local/venvs/platform/bin/python manage.py collectstatic --noinput
/usr/local/venvs/platform/bin/python manage.py migrate

chown -R www-data:www-data /var/log/helium /var/log/apache2

service supervisor start; apache2ctl -D FOREGROUND
