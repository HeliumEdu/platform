__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.8"

from datetime import timedelta

from celery import states
from celery.exceptions import TaskRevokedError
from django.conf import settings
from django.utils import timezone
from django_celery_results.models import TaskResult
from health_check.backends import BaseHealthCheckBackend
from health_check.cache.backends import CacheBackend
from health_check.contrib.celery.backends import CeleryHealthCheck
from health_check.contrib.celery.tasks import add
from health_check.contrib.s3boto3_storage.backends import S3Boto3StorageHealthCheck
from health_check.db.backends import DatabaseBackend
from health_check.exceptions import HealthCheckException, ServiceUnavailable


class IdentifiedDatabaseBackend(DatabaseBackend):
    def identifier(self):
        return "Database"


class IdentifiedCacheBackend(CacheBackend):
    def identifier(self):
        return "Cache"


class IdentifiedS3Boto3StorageHealthCheck(S3Boto3StorageHealthCheck):
    def identifier(self):
        return "Storage"


class IdentifiedCeleryHealthCheck(CeleryHealthCheck):
    def check_status(self):
        timeout = getattr(settings, 'HEALTHCHECK_CELERY_TIMEOUT', 3)

        try:
            for queue in self.queues:
                result = add.apply_async(
                    args=[4, 4],
                    expires=timeout,
                    queue=queue
                )
                result.get(timeout=timeout)
                if result.result != 8:
                    self.add_error(ServiceUnavailable(
                        f"Celery returned wrong result for queue {queue}"))
        except IOError as e:
            self.add_error(ServiceUnavailable("IOError"), e)
        except (TimeoutError, TaskRevokedError):
            # Expected failures when workers are busy - report as unhealthy
            # without logging exception traceback to Sentry
            self.add_error(ServiceUnavailable(
                "Celery workers busy or unresponsive"))
        except BaseException as e:
            self.add_error(ServiceUnavailable("Unknown error"), e)

    def identifier(self):
        return "TaskProcessing"


class IdentifiedCeleryBeatHealthCheck(BaseHealthCheckBackend):
    def check_status(self):
        try:
            time_threshold = timezone.now() - timedelta(minutes=3)
            if not TaskResult.objects.filter(date_done__gte=time_threshold,
                                             status=states.SUCCESS).exists():
                self.add_error("CeleryBeat check failed: no recent results.")
        except Exception as e:
            raise HealthCheckException(f"CeleryBeat health check failed: {e}")

    def identifier(self):
        return "CeleryBeat"
