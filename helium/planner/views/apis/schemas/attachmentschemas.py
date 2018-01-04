import logging

import coreapi
import coreschema
from rest_framework.schemas import AutoSchema

from helium.common.views.apis.schemas.baseschemas import BaseIDSchema
from helium.planner.models import Attachment

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class AttachmentListSchema(AutoSchema):
    def get_link(self, path, method, base_url):
        link = super(AttachmentListSchema, self).get_link(path, method, base_url)

        if method == 'POST':
            fields = [
                coreapi.Field(
                    "file[]",
                    required=False,
                    location="form",
                    schema=coreschema.String(title='file[]',
                                             description='A multipart list of files to upload.')
                ),
                coreapi.Field(
                    "course",
                    required=False,
                    location="form",
                    schema=coreschema.Integer(title='course',
                                              description=Attachment._meta.get_field('course').help_text)
                ),
                coreapi.Field(
                    "event",
                    required=False,
                    location="form",
                    schema=coreschema.Integer(title='event',
                                              description=Attachment._meta.get_field('event').help_text)
                ),
                coreapi.Field(
                    "homework",
                    required=False,
                    location="form",
                    schema=coreschema.Integer(title='homework',
                                              description=Attachment._meta.get_field('homework').help_text)
                )
            ]

            return coreapi.Link(
                url=link.url,
                action=link.action,
                encoding=link.encoding,
                fields=fields,
                description=link.description
            )

        return link

    def modify_options_response(self, response):
        response.data['actions']['POST'].pop('id')
        response.data['actions']['POST'].pop('title')
        response.data['actions']['POST'].pop('attachment')
        response.data['actions']['POST'].pop('size')

        response.data['actions']['POST']['file[]'] = {
            "type": "file upload",
            "required": True,
            "read_only": False,
            "label": "Files",
            "help_text": "A multipart list of files to upload."
        }


class AttachmentDetailSchema(BaseIDSchema):
    def __init__(self):
        super(AttachmentDetailSchema, self).__init__('attachment')
