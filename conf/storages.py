"""
Storages for funneling Pipelines to storage destinations.
"""
from django.conf import settings

from pipeline.storage import PipelineMixin

from storages.backends.s3boto import S3BotoStorage

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.2'


class S3StaticPipelineStorage(PipelineMixin, S3BotoStorage):
    def __init__(self, *args, **kwargs):
        super(S3StaticPipelineStorage, self).__init__(*args, **kwargs)
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME


class S3MediaPipelineStorage(PipelineMixin, S3BotoStorage):
    def __init__(self, *args, **kwargs):
        super(S3MediaPipelineStorage, self).__init__(*args, **kwargs)
        self.bucket_name = settings.AWS_MEDIA_STORAGE_BUCKET_NAME
        self.custom_domain = None
