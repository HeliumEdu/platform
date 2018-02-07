import os
from tempfile import NamedTemporaryFile

from django.core.files.uploadedfile import SimpleUploadedFile

from helium.planner.models import Attachment

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

tmp_files = []


def given_file_exists(ext='.txt'):
    global tmp_files

    tmp_file = NamedTemporaryFile(suffix=ext, delete=False)
    tmp_file.write("Attachment File".encode())
    tmp_file.close()

    tmp_files.append(tmp_file)

    return tmp_file


def given_attachment_exists(user, course=None, event=None, homework=None):
    uploaded_file = SimpleUploadedFile('myfile.txt', 'Attachment File'.encode())

    attachment = Attachment.objects.create(title=uploaded_file.name,
                                           attachment=uploaded_file,
                                           course=course,
                                           event=event,
                                           homework=homework,
                                           user=user)

    return attachment


def verify_attachment_matches_data(test_case, attachment, data):
    test_case.assertEqual(attachment.title, data['title'])
    test_case.assertEqual(attachment.size, data['size'])
    if 'course' in data and data['course']:
        test_case.assertEqual(attachment.course.pk, data['course'])
    if 'event' in data and data['event']:
        test_case.assertEqual(attachment.event.pk, data['event'])
    if 'homework' in data and data['homework']:
        test_case.assertEqual(attachment.homework.pk, data['homework'])
    test_case.assertEqual(attachment.user.pk, data['user'])


def cleanup_attachments():
    global tmp_files

    for tmp_file in tmp_files:
        os.remove(tmp_file.name)

    tmp_files = []

    for attachment in Attachment.objects.all():
        attachment.delete()
