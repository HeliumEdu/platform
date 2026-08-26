"""
Storages for funneling Pipelines to storage destinations.
"""

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

    def url(self, name, parameters=None, expire=None, http_method=None):
        """
        Sign the URL with a download disposition so every object saves rather than renders,
        including any stored without one of its own.

        No filename is set: it would be user input, and the key already ends with the
        original name.
        """
        parameters = dict(parameters or {})
        parameters.setdefault('ResponseContentDisposition', 'attachment')
        return super().url(name, parameters=parameters, expire=expire,
                           http_method=http_method)
