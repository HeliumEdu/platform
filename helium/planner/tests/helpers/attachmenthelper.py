"""
Helper for Attachment models (and associated files) in testing.
"""
from tempfile import NamedTemporaryFile

from django.core.files.uploadedfile import SimpleUploadedFile

from helium.planner.models import Attachment

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


def given_file_exists():
    tmp_file = NamedTemporaryFile(delete=False)
    tmp_file.write("Attachment File")
    tmp_file.close()

    return tmp_file


def given_attachment_exists(user, course=None):
    uploaded_file = SimpleUploadedFile('myfile.txt', 'Attachment File')

    attachment = Attachment.objects.create(title=uploaded_file.name,
                                           attachment=uploaded_file,
                                           course=course,
                                           user=user)

    return attachment


def verify_attachment_matches_data(test_case, attachment, data):
    test_case.assertEqual(attachment.title, data['title'])
    test_case.assertEqual(attachment.size, data['size'])
    if 'course' in data:
        test_case.assertEqual(attachment.course.pk, data['course'])
    if 'event' in data:
        test_case.assertEqual(attachment.event.pk, data['event'])
    if 'homework' in data:
        test_case.assertEqual(attachment.homework.pk, data['homework'])
    if 'user' in data:
        test_case.assertEqual(attachment.user.pk, data['user'])
