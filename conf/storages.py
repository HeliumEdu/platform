"""
Storages for funneling Pipelines to storage destinations.
"""

__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.conf import settings

from pipeline.storage import PipelineMixin

from storages.backends.s3boto3 import S3Boto3Storage


class S3StaticPipelineStorage(PipelineMixin, S3Boto3Storage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME


class S3MediaPipelineStorage(PipelineMixin, S3Boto3Storage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bucket_name = settings.AWS_MEDIA_STORAGE_BUCKET_NAME
        self.custom_domain = None
