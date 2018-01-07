import logging

import coreapi
import coreschema
from rest_framework.schemas import AutoSchema

from helium.common.schemas import BaseIDSchema
from helium.planner.models import Attachment, Course, Category, Material

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


class SubCourseGroupListSchema(AutoSchema):
    """
    If Django Rest Framework adds better support for properly getting the `help_text` of related fields,
    this can be removed
    """

    def __init__(self, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field(
                "course_group",
                required=True,
                location="path",
                schema=coreschema.Integer(title='id',
                                          description=Course._meta.get_field('course_group').help_text)
            ),
        ]

        super(SubCourseGroupListSchema, self).__init__(manual_fields=manual_fields)


class CourseGroupDetailSchema(BaseIDSchema):
    def __init__(self):
        super(CourseGroupDetailSchema, self).__init__('course group')


class SubCourseListSchema(SubCourseGroupListSchema):
    def __init__(self, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field(
                "course",
                required=True,
                location="path",
                schema=coreschema.Integer(title='id',
                                          description=Category._meta.get_field('course').help_text)
            ),
        ]

        super(SubCourseListSchema, self).__init__(manual_fields=manual_fields)


class CourseDetailSchema(BaseIDSchema, SubCourseGroupListSchema):
    def __init__(self):
        super(CourseDetailSchema, self).__init__('course')


class CategoryDetailSchema(BaseIDSchema, SubCourseListSchema):
    def __init__(self):
        super(CategoryDetailSchema, self).__init__('category')


class EventDetailSchema(BaseIDSchema):
    def __init__(self):
        super(EventDetailSchema, self).__init__('event')


class HomeworkDetailSchema(BaseIDSchema, SubCourseListSchema):
    def __init__(self):
        super(HomeworkDetailSchema, self).__init__('homework')


class SubMaterialGroupListSchema(AutoSchema):
    def __init__(self, manual_fields=None):
        if manual_fields is None:
            manual_fields = []

        manual_fields += [
            coreapi.Field(
                "material_group",
                required=True,
                location="path",
                schema=coreschema.Integer(title='id',
                                          description=Material._meta.get_field('material_group').help_text)
            ),
        ]

        super(SubMaterialGroupListSchema, self).__init__(manual_fields=manual_fields)


class MaterialGroupDetailSchema(BaseIDSchema):
    def __init__(self):
        super(MaterialGroupDetailSchema, self).__init__('material group')


class MaterialDetailSchema(BaseIDSchema, SubMaterialGroupListSchema):
    def __init__(self):
        super(MaterialDetailSchema, self).__init__('material')


class ReminderDetailSchema(BaseIDSchema):
    def __init__(self):
        super(ReminderDetailSchema, self).__init__('reminder')
