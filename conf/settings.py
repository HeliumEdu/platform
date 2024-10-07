"""
This generic settings builder reads the appropriate configuration file for different methods of deployment.

Note that the system environment variable ENVIRONMENT should be set to a slug that matches the deployed environment.

* If ENVIRONMENT is set to `dev`, `local.py` will be used for configuration, using values from `.env`
* If ENVIRONMENT is not `dev`, `deploy.py` will be used for configuration, using system environment variables
* If `test` is passed as an argument, ENVIRONMENT is ignored and `test.py` is used for configuration, reading from `.env`

All configuration files first read `common.py` before applying deployment-specific configurations.
"""

__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.7.2"

import sys

from decouple import config

# Are we running on the dev server
DEV_SERVER = False

if 'test' not in sys.argv:
    if config('ENVIRONMENT').lower() == 'local' or (len(sys.argv) > 1 and sys.argv[1] == 'runserver'):
        conf = 'local'
        if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
            DEV_SERVER = True
    else:
        conf = 'deploy'
# If we're running tests, run a streamlined settings file for efficiency
else:
    conf = 'test'

# Initialize some global settings
locals()['DEV_SERVER'] = DEV_SERVER
PROJECT_ID = "helium"
locals()['PROJECT_ID'] = PROJECT_ID

# Load conf properties into the local scope
print(f'Using conf.configs.{conf}')
common_conf_module = __import__('conf.configs.common', globals(), locals(), [PROJECT_ID])
conf_module = __import__(f'conf.configs.{conf}', globals(), locals(), [PROJECT_ID])

# Load common conf properties into the local scope
for setting in dir(common_conf_module):
    if setting == setting.upper():
        locals()[setting] = getattr(common_conf_module, setting)

# Load env-specific properties into the local scope
for setting in dir(conf_module):
    if setting == setting.upper():
        locals()[setting] = getattr(conf_module, setting)
