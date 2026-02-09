__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import sys
from urllib.parse import urlparse

import firebase_admin
from django.apps import AppConfig
from django.conf import settings
from firebase_admin import credentials
from health_check.plugins import plugin_dir


class CommonConfig(AppConfig):
    name = 'helium.common'
    verbose_name = 'Common'

    def ready(self):
        self.init_ngrok()

        self.init_firebase()

        plugin_dir.reset()

        from helium.common.health import IdentifiedDatabaseBackend, IdentifiedCacheBackend, \
            IdentifiedS3Boto3StorageHealthCheck, IdentifiedCeleryHealthCheck, IdentifiedCeleryBeatHealthCheck

        plugin_dir.register(IdentifiedDatabaseBackend, database_name='default')
        plugin_dir.register(IdentifiedCacheBackend, backend='default')
        plugin_dir.register(IdentifiedS3Boto3StorageHealthCheck)
        plugin_dir.register(type("TaskProcessing", (IdentifiedCeleryHealthCheck,), {'queue': 'celery'}))
        plugin_dir.register(IdentifiedCeleryBeatHealthCheck)

    def init_ngrok(self):
        if settings.USE_NGROK:
            # pyngrok will only be installed, and should only ever be initialized, in a dev environment
            from pyngrok import ngrok, installer
            from pyngrok.conf import DEFAULT_NGROK_CONFIG_PATH

            # Get the dev server port (defaults to 8000 for Django, can be overridden with the
            # last arg when calling `runserver`)
            addrport = urlparse(f"http://{sys.argv[-1]}")
            port = addrport.port if addrport.netloc and addrport.port else 8000

            # Open a ngrok tunnel to the dev server
            config = installer.get_ngrok_config(DEFAULT_NGROK_CONFIG_PATH)
            if "tunnels" not in config or "heliumedu" not in config["tunnels"]:
                print("ERROR:  Tunnel 'heliumedu' is not defined in the config files.")
                print(f"ERROR:  Config files read: [{DEFAULT_NGROK_CONFIG_PATH}]")
                sys.exit(1)
            frontend_ngrok_domain = config["tunnels"]["heliumedu"]["domain"]
            public_url = ngrok.connect(name="heliumedu", addr=port, domain=f"api.{frontend_ngrok_domain}").public_url
            print(f"ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{port}\"")

    def init_firebase(self):
        if settings.FIREBASE_CREDENTIALS:
            firebase_admin.initialize_app(credential=credentials.Certificate(settings.FIREBASE_CREDENTIALS))
