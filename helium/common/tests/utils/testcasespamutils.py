from django.test import TestCase

from helium.common.utils.spamutils import detect_solicitation, find_signals

SPAM = {
    'lead_gen': (
        'Partnership opportunity — Acme Leads',
        "Hi, I'm Jane Doe, founder of Acme Leads. We are the only company that guarantees sales qualified MQLs "
        '(not just leads) in your ICP (Ideal Customer Profile), using our platform. More here: '
        'www.acmeleads.example/pricing\n\nSchedule a call with me: https://acmeleads.zohobookings.com/#/1234567890',
    ),
    'outreach_agency': (
        'Guaranteed Results or Your Money Back',
        "Hi, I’m John Roe, the founder of Example Outreach. We help businesses achieve measurable results through "
        'highly targeted outreach. If we fall short by even one agreed result, we’ll refund you in full. You can '
        'schedule a time here: https://calendly.com/example/30min',
    ),
    'launch_ranking': (
        'Can we promote you on Uneed for 1st rank?',
        'Can we get you 1st rank on your Uneed Launch today just in $40\n\n'
        'Contact us:\nWhatsApp: https://wa.me/15555550100\nWEB: https://rank.example/product/',
    ),
}

LEGITIMATE = {
    'self_hosting': (
        'Self hosting Helium',
        "I'm interested in self hosting Helium for personal use. Would you have documentation on the procedure?",
    ),
    'off_by_one_day': (
        "Planner doesn't put things on the right date",
        'In the planner all of the events and tasks show up one day before the actual date. This also goes for '
        'external synced calendars.',
    ),
    'llm_written': (
        'Assignments Not Syncing Between Devices',
        'Dear Helium Support Team,\n\nI hope this message finds you well. I am writing to report an issue I have '
        'been experiencing — assignments I create on my phone do not appear on the web version.\n\nI would greatly '
        'appreciate any guidance you could provide. I would be happy to schedule a time to discuss further.\n\n'
        'Best regards,\nAlex',
    ),
    'synced_google_calendar': (
        'Meetings missing from synced calendar',
        'When I schedule a meeting in Google Calendar it does not show up in Helium. Here is the calendar I synced: '
        'https://calendar.google.com/calendar/ical/example/basic.ics',
    ),
    'professor_office_hours': (
        'Office hours not importing',
        'My professor posts office hours at https://calendly.com/professor/office-hours but I cannot import them.',
    ),
    'journalist': (
        'Interview request',
        "Hi, I'm a reporter hoping to interview the founder of Helium for The Daily Campus. Can we schedule a "
        'quick call? Book a time with me here: https://calendly.com/reporter/15min',
    ),
    'tutoring_center': (
        'Rolling Helium out to our students',
        "I'm the founder of a tutoring center. We help students stay organized and want to roll Helium out to 400 "
        'students. Can we set up a call with you? We can guarantee feedback.',
    ),
}

EVERYDAY_PHRASING = [
    'When I try to pick a time for my class the time picker resets to 12:00.',
    "I can't schedule a time block for studying, the button does nothing.",
    "I want to book a slot in my calendar for office hours but Helium won't let me.",
    'If I schedule a call with my study group as an event it shows up on the wrong day.',
    'I donated just $5 on Patreon. Is my data guaranteed to be backed up?',
    "Can you guarantee my grades won't be lost if I switch phones?",
    "I'm the outreach chair for my school's robotics club and want to share Helium with members.",
    'Our agency wants to know if Helium is FERPA compliant. Could we hop on a call?',
    "I'm a student writing about the founder of Helium for class.",
    'Is there SEO work needed on the marketing site? I would love to contribute.',
    'You can reach me at jane@calendly.com or on my site at my.cal.com.au.',
]


class TestCaseSpamUtils(TestCase):
    def test_spam_flagged(self):
        for name, (subject, description) in SPAM.items():
            with self.subTest(name):
                # WHEN
                signals = detect_solicitation(subject, description)

                # THEN
                self.assertIn('booking_link', signals)
                self.assertGreaterEqual(len(signals), 3)

    def test_legitimate_not_flagged(self):
        for name, (subject, description) in LEGITIMATE.items():
            with self.subTest(name):
                # WHEN
                signals = detect_solicitation(subject, description)

                # THEN
                self.assertEqual(signals, [])

    def test_everyday_phrasing_has_no_signals(self):
        for description in EVERYDAY_PHRASING:
            with self.subTest(description):
                # WHEN
                signals = find_signals('', description)

                # THEN
                self.assertEqual(signals, [])

    def test_three_signals_without_booking_link_flagged(self):
        # WHEN
        signals = detect_solicitation('Grow your user base',
                                      'We help startups like yours with targeted outreach. Results guaranteed. '
                                      'Grab a quick call with us this week?')

        # THEN
        self.assertCountEqual(signals, ['call_to_action', 'vendor_pitch', 'offer_guarantee', 'lead_gen_jargon'])

    def test_two_signals_not_flagged(self):
        # WHEN
        signals = detect_solicitation('Have any writing needs?',
                                      'I am a freelance writer. You can book a time with me to chat if interested: '
                                      'https://calendly.com/example/30min')

        # THEN
        self.assertEqual(signals, [])

    def test_zero_width_characters_stripped(self):
        # WHEN
        signals = find_signals('Quick question',
                               'Book a call with us, results guaranteed: https://cal\u2060endly.com/example')

        # THEN
        self.assertEqual(signals, ['booking_link', 'call_to_action', 'offer_guarantee'])
