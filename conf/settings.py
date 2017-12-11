"""
Entry point for building settings and other configuration parameters.
"""

import os
import sys
from builtins import str

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

    if conf == 'dev':
        print('Loading .env file')

        import dotenv

        dotenv.read_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), True)
# If we're running tests, run a streamlined settings file for efficiency
else:
    conf = 'test'

    print('Loading .env file')

    import dotenv

    dotenv.read_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), True)

# Load conf properties into the local scope
print('Using conf.configs.{}'.format(conf))
common_conf_module = __import__('conf.configs.common', globals(), locals(), 'helium')
conf_module = __import__('conf.configs.{}'.format(conf), globals(), locals(), 'helium')

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
    connection.connection.text_factory = lambda x: str(x)
