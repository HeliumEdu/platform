import os
import re

from django.template.loader import get_template
from django.test import SimpleTestCase
from django.utils import timezone, translation

_SNAPSHOTS = os.path.join(os.path.dirname(__file__), 'resources', 'email')

_SUPPORT_URL = 'https://www.heliumedu.com/support/'
_LOGIN_URL = 'https://app.heliumedu.com/signin'

_DORMANT_CONTEXT = {
    'dormancy_years': 2,
    'login_url': _LOGIN_URL,
    'export_url': f'{_SUPPORT_URL}import-export-and-backup/importing-and-exporting-your-data/',
    'delete_account_url': f'{_SUPPORT_URL}account/deleting-your-account-and-data/',
    'support_url': _SUPPORT_URL,
}

EMAIL_CASES = {
    'register': ('email/register', {'login_url': _LOGIN_URL}),
    'verification': ('email/verification', {
        'email': 'test+1@example.com',
        'verification_code': 123456,
        'verify_url': 'https://app.heliumedu.com/verify',
    }),
    'forgot': ('email/forgot', {
        'reset_url': 'https://app.heliumedu.com/reset?uid=abc&token=def',
        'support_url': _SUPPORT_URL,
    }),
    'dormant_warning': ('email/dormant_warning', {
        **_DORMANT_CONTEXT,
        'subject': 'Your Account Will Be Deleted in 30 Days',
        'days_remaining': 30,
        'is_final_warning': False,
    }),
    'dormant_warning_final': ('email/dormant_warning', {
        **_DORMANT_CONTEXT,
        'subject': 'Final Notice: Account Deletion Tomorrow',
        'days_remaining': 1,
        'is_final_warning': True,
    }),
    'reminder_homework': ('email/reminder', {
        'subject': 'Essay 1 in Writing 101 in 30 minutes',
        'reminder': {'message': 'Turn in the essay', 'homework': True},
        'calendar_item': {
            'category': {'title': 'Papers'},
            'course': {'title': 'Writing 101', 'website': 'https://example.com/w101', 'room': 'Room 12',
                       'is_online': False},
            'resources': {'count': 1, 'all': [{'title': 'Style Guide', 'website': 'https://example.com/guide'}]},
            'attachments': {'count': 1, 'all': [{'title': 'draft.pdf'}]},
        },
        'normalized_datetime': 'Fri, Sep 4 at 3:05 PM',
        'note_url': 'https://app.heliumedu.com/notebook/1',
        'open_url': 'https://app.heliumedu.com/planner/assignments/1',
        'attachments_url': 'https://app.heliumedu.com/planner/assignments/1/attachments',
    }),
    'reminder_course': ('email/reminder', {
        'subject': 'Biology in 1 hour',
        'reminder': {'message': 'Class soon', 'course': True},
        'calendar_item': {
            'title': 'Biology',
            'website': 'https://example.com/bio',
            'room': 'Lab 3',
            'is_online': False,
            'teacher_name': 'Dr. Smith',
            'teacher_email': 'smith@example.com',
        },
        'normalized_datetime': 'Fri, Sep 4 at 9:00 AM to 10:15 AM',
        'note_url': '',
        'open_url': 'https://app.heliumedu.com/classes/1',
        'attachments_url': '',
    }),
}


def render_email(case):
    template_name, context = EMAIL_CASES[case]
    return (get_template(f'{template_name}.txt').render(context),
            get_template(f'{template_name}.html').render(context))


def _snapshot(case, extension):
    with open(os.path.join(_SNAPSHOTS, f'{case}.{extension}'), encoding='utf-8') as f:
        return f.read().replace('{{ year }}', str(timezone.now().year))


def _collapse_whitespace(html):
    return re.sub(r'\s+', ' ', html).strip()


class TestCaseEmailTemplates(SimpleTestCase):
    def test_english_renders_unchanged(self):
        for case in EMAIL_CASES:
            with self.subTest(case=case):
                # WHEN
                with translation.override('en'):
                    text, html = render_email(case)

                # THEN
                self.assertEqual(_snapshot(case, 'txt'), text)
                self.assertEqual(_collapse_whitespace(_snapshot(case, 'html')), _collapse_whitespace(html))
