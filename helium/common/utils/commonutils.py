__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import csv
import datetime
import io
import logging
import random
import smtplib
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template

from helium.auth.utils.userutils import is_staff_email
from helium.common import enums
from helium.common.utils import metricutils

logger = logging.getLogger(__name__)

_ses_client = None


class HeliumError(Exception):
    pass


class EmailSuppressedException(HeliumError):
    """Raised when an email send fails due to a rejected recipient and the address has been suppressed."""

    def __init__(self, email, original_error=None):
        self.email = email
        self.original_error = original_error
        super().__init__('Email was suppressed due to rejected recipient')


def _get_ses_client():
    global _ses_client
    if _ses_client is None:
        import boto3
        _ses_client = boto3.client('sesv2', region_name=settings.AWS_REGION)
    return _ses_client


def redact_email(email: str) -> str:
    """
    Redact an email address for safe logging. Preserves the first character of the local part,
    the first character of the domain, and the TLD.

    :param email: The email address to redact
    :return: A redacted representation, e.g. ``j***@g***.com``
    """
    try:
        local, domain = email.rsplit('@', 1)
        domain_name, tld = domain.rsplit('.', 1)
        return f'{local[0]}***@{domain_name[0]}***.{tld}'
    except (ValueError, IndexError):
        return '***'


def clear_ses_suppression_if_exists(email: str) -> bool:
    """
    Remove an email from the SES account suppression list if present.

    This handles the edge case where a previously-bounced email address is now owned
    by a different person attempting to register (e.g., recycled .edu addresses).

    :param email: The email address to remove from suppression
    :return: True if the email was removed, False if it wasn't suppressed
    """
    if settings.DISABLE_EMAILS:
        return False

    try:
        from botocore.exceptions import ClientError
        _get_ses_client().delete_suppressed_destination(EmailAddress=email)
        logger.info(f'Removed {redact_email(email)} from SES suppression list')
        metricutils.increment('ses.suppression.cleared')
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'NotFoundException':
            return False
        logger.warning(f'Failed to clear SES suppression for {redact_email(email)}: {e}')
        metricutils.increment('ses.suppression.check_failed')
        return False
    except Exception as e:
        logger.warning(f'Failed to clear SES suppression for {redact_email(email)}: {e}')
        metricutils.increment('ses.suppression.check_failed')
        return False


def add_to_ses_suppression_list(email: str, reason: str = 'BOUNCE') -> bool:
    """
    Add an email to the SES account suppression list.

    :param email: The email address to suppress
    :param reason: SES suppression reason — ``'BOUNCE'`` (default) or ``'COMPLAINT'``
    :return: True if the email was added, False on failure
    """
    if settings.DISABLE_EMAILS:
        return False

    if is_staff_email(email):
        logger.info(f'Skipping SES suppression for staff email {redact_email(email)}')
        return False

    try:
        _get_ses_client().put_suppressed_destination(
            EmailAddress=email,
            Reason=reason,
        )
        logger.info(f'Added {redact_email(email)} to SES suppression list (reason={reason})')
        metricutils.increment('ses.suppression.added')
        return True

    except Exception as e:
        logger.warning(f'Failed to add {redact_email(email)} to SES suppression list: {e}')
        metricutils.increment('ses.suppression.add_failed')
        return False


def send_multipart_email(template_name, context, subject, to, bcc=None, email_type=None):
    """
    Send a multipart text/html email.

    :param template_name: The path to the template (no extension), assuming both a .txt and .html version are present
    :param context: A dictionary of context elements to pass to the email templates
    :param subject: The subject of the email
    :param to: A list of email addresses to which to send
    :param bcc: A list of email addresses to which to BCC
    :param email_type: The type of email for metric tagging (e.g. "reminder", "registration", "verification")
    :return:
    """
    plaintext = get_template(f'{template_name}.txt')
    html = get_template(f'{template_name}.html')
    text_content = plaintext.render(context)
    html_content = html.render(context)

    msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, to, bcc)
    msg.extra_headers['X-SES-CONFIGURATION-SET'] = settings.SES_CONFIGURATION_SET
    if email_type:
        msg.extra_headers['X-SES-MESSAGE-TAGS'] = f'email_type={email_type}'
    msg.attach_alternative(html_content, "text/html")

    extra_tags = [f"type:{email_type}"] if email_type else []

    try:
        msg.send()
        logger.debug(f"Sent email successfully to {len(to)} recipient(s)")
        metricutils.increment('action.email.sent', extra_tags=extra_tags)
        if email_type == 'reminder':
            metricutils.increment('action.reminder.sent', extra_tags=['channel:email'])
    except smtplib.SMTPRecipientsRefused as e:
        logger.warning(f"Recipients refused by SES: {e.recipients}")
        metricutils.increment('action.email.failed', extra_tags=extra_tags)
        for rejected_email in e.recipients:
            add_to_ses_suppression_list(rejected_email)
        raise EmailSuppressedException(to, original_error=e) from e
    except smtplib.SMTPDataError as e:
        logger.warning(f"SES rejected message data: {e.smtp_code} {e.smtp_error}")
        metricutils.increment('action.email.failed', extra_tags=extra_tags)
        raise EmailSuppressedException(to, original_error=e) from e
    except ValueError as e:
        logger.warning(f"Invalid email address: {e}")
        metricutils.increment('action.email.failed', extra_tags=extra_tags)
        raise EmailSuppressedException(to, original_error=e) from e
    except Exception:
        logger.error("Failed to send email", exc_info=True)
        metricutils.increment('action.email.failed', extra_tags=extra_tags)
        raise


def send_support_contact_email(subject, category, email, description, attachments=None):
    """
    Compose and send a plain-text support contact email via SES to the JSM email
    channel. The submitter's address is set as ``Reply-To`` so JSM treats them as
    the requester on the resulting ticket.

    Reaching out via the support form is an explicit signal that the user wants
    bidirectional contact — if their address was previously bounced/complained
    and added to the SES suppression list, clear it here so future transactional
    mail (and any direct SES correspondence) can reach them again. Mirrors the
    pattern used during registration.

    :param subject: User-supplied subject line.
    :param category: Validated category label (e.g. ``Bug Report``).
    :param email: Validated submitter email address; used as Reply-To.
    :param description: Free-form body content.
    :param attachments: Iterable of uploaded files (Django ``UploadedFile``-like).
    :raises EmailSuppressedException: If SES rejects the message or transport fails.
    """
    clear_ses_suppression_if_exists(email)

    full_subject = f'[{settings.PROJECT_NAME} Support] {category}: {subject}'
    body = (
        f'From: {email}\n'
        f'Category: {category}\n'
        f'\n'
        f'{description}\n'
    )

    msg = EmailMultiAlternatives(
        subject=full_subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.SUPPORT_INBOX_EMAIL],
        reply_to=[email],
    )
    msg.extra_headers['X-SES-CONFIGURATION-SET'] = settings.SES_CONFIGURATION_SET
    msg.extra_headers['X-SES-MESSAGE-TAGS'] = 'email_type=support_contact'

    for f in attachments or ():
        msg.attach(f.name, f.read(), getattr(f, 'content_type', None) or 'application/octet-stream')

    try:
        msg.send()
        metricutils.increment('action.support_contact.sent')
        logger.info(f'Support contact relayed from {redact_email(email)} ({category})')
    except smtplib.SMTPRecipientsRefused as e:
        logger.warning(f'SES refused support contact recipients: {e.recipients}')
        metricutils.increment('action.support_contact.failed')
        raise EmailSuppressedException(settings.SUPPORT_INBOX_EMAIL, original_error=e) from e
    except smtplib.SMTPDataError as e:
        logger.warning(f'SES rejected support contact message data: {e.smtp_code} {e.smtp_error}')
        metricutils.increment('action.support_contact.failed')
        raise EmailSuppressedException(settings.SUPPORT_INBOX_EMAIL, original_error=e) from e
    except ValueError as e:
        logger.warning(f'Invalid support contact email address: {e}')
        metricutils.increment('action.support_contact.failed')
        raise EmailSuppressedException(settings.SUPPORT_INBOX_EMAIL, original_error=e) from e
    except Exception:
        logger.error('Failed to send support contact email', exc_info=True)
        metricutils.increment('action.support_contact.failed')
        raise


def remove_exponent(d):
    """
    Remove the exponent, which may be present in a Decimal.

    :param d: the Decimal number which may contain an exponent
    :return: a number without an exponent
    """
    return d.quantize(Decimal(1)) if d == d.to_integral() else d.normalize()


def calculate_trend(series_range, series_list):
    """
    With the given range and list, calculate the linear regression such that the returned value illustrates if the
    numbers are trending positive or negative.

    :param series_range: A range of values against which to calculate a linear regression.
    :param series_list: The list of numbers to calculate the linear regression against.
    :return: The calculated trend of the range and list, or None if the determinate indicates no trend.
    """
    range_count = len(series_range)
    x = 0
    y = 0
    xx = 0
    yy = 0
    sx = 0

    for range_item, list_item in zip(series_range, series_list):
        x += range_item
        y += list_item
        xx += range_item * range_item

        yy += list_item * list_item
        sx += range_item * list_item

    d = xx * range_count - x * x

    if d != 0:
        return (sx * range_count - y * x) / d
    else:
        return None


def split_csv(s, delimiter=',', quotechar="'"):
    f = io.StringIO(s)
    reader = csv.reader(f, delimiter=delimiter, quotechar=quotechar)
    for row in reader:
        return row


def random_color():
    return random.choice(enums.PREFERRED_COLORS)


def local_midnight_as_utc(date, tz):
    """
    Return the UTC datetime that represents midnight on the given date in the given timezone.

    :param date: A `date` (or `datetime`, of which only the date portion is used).
    :param tz: A `tzinfo` (e.g. `ZoneInfo`) representing the local timezone.
    :return: An aware UTC `datetime` at midnight `tz` on `date`.
    """
    naive = datetime.datetime(date.year, date.month, date.day, 0, 0, 0, 0)
    aware = naive.replace(tzinfo=tz)
    return aware.astimezone(datetime.timezone.utc)


def format_short_time(dt):
    """
    Format a datetime as a short time string, omitting minutes when they are zero.
    e.g. 11:00 AM -> "Tue, 11 AM", 11:30 AM -> "Tue, 11:30 AM", 1:00 PM -> "Tue, 1 PM"
    """
    if dt.minute == 0:
        time_str = dt.strftime('%I %p').lstrip('0')
    else:
        time_str = dt.strftime('%I:%M %p').lstrip('0')

    return f'{dt.strftime("%a")}, {time_str}'
