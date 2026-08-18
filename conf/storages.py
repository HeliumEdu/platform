"""
Storages for funneling Pipelines to storage destinations.
"""

__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

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
        # Serve user-uploaded media as a download so it cannot render inline.
        self.object_parameters = {'ContentDisposition': 'attachment'}
