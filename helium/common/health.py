__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from datetime import timedelta

from celery import states
from django.utils import timezone
from django_celery_results.models import TaskResult
from health_check.backends import BaseHealthCheckBackend
from health_check.cache.backends import CacheBackend
from health_check.contrib.celery.backends import CeleryHealthCheck
from health_check.contrib.s3boto3_storage.backends import S3Boto3StorageHealthCheck
from health_check.db.backends import DatabaseBackend
from health_check.exceptions import HealthCheckException


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
