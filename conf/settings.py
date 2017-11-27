"""
Entry point for building settings and other configuration parameters.
"""

import os
import sys

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

# Are we running on the dev server
DEV_SERVER = False

if 'test' not in sys.argv:
    if os.environ.get('ENVIRONMENT') == 'dev' or (len(sys.argv) > 1 and sys.argv[1] == 'runserver'):
        conf = 'dev'
        if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
            DEV_SERVER = True
    else:
        conf = 'deploy'

    print 'Using conf: conf.configs.%s' % conf

    if conf == 'dev':
        print 'Loading .env file'

        from dotenv import Dotenv

        dotenv = Dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
        os.environ.update(dotenv)

    # Load conf properties into the local scope
    conf_module = __import__('conf.configs.%s' % conf, globals(), locals(), 'helium')
# If we're running tests, run a streamlined settings file for efficiency
else:
    print 'Loading .env file'

    from dotenv import Dotenv

    dotenv = Dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    os.environ.update(dotenv)

    conf_module = __import__('conf.configs.test', globals(), locals(), 'helium')

common_conf_module = __import__('conf.configs.common', globals(), locals(), 'helium')

# Load common conf properties into the local scope
for setting in dir(common_conf_module):
    if setting == setting.upper():
        locals()[setting] = getattr(common_conf_module, setting)

# Load env-specific properties into the local scope
for setting in dir(conf_module):
    if setting == setting.upper():
        locals()[setting] = getattr(conf_module, setting)

locals()['DEV_SERVER'] = DEV_SERVER

# Special configuration if we are using SQLite
if conf_module.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    from django.db import connection

    connection.cursor()
    connection.connection.text_factory = lambda x: unicode(x, "utf-8", "ignore")
