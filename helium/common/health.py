from health_check.cache.backends import CacheBackend
from health_check.contrib.celery.backends import CeleryHealthCheck
from health_check.contrib.s3boto3_storage.backends import S3Boto3StorageHealthCheck
from health_check.db.backends import DatabaseBackend


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
