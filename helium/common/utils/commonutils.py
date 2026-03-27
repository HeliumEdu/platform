__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import csv
import io
import logging
import random
import smtplib
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template

from helium.common import enums
from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


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
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client('sesv2', region_name=settings.AWS_REGION)

        try:
            client.delete_suppressed_destination(EmailAddress=email)
            logger.info(f'Removed {redact_email(email)} from SES suppression list')
            metricutils.increment('ses.suppression.cleared')
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'NotFoundException':
                return False
            raise

    except Exception as e:
        logger.warning(f'Failed to clear SES suppression for {redact_email(email)}: {e}')
        metricutils.increment('ses.suppression.check_failed')
        return False


class HeliumError(Exception):
    pass


class EmailSuppressedException(HeliumError):
    """Raised when an email send fails due to a rejected recipient and the address has been suppressed."""

    def __init__(self, email, original_error=None):
        self.email = email
        self.original_error = original_error
        super().__init__('Email was suppressed due to rejected recipient')


def add_to_ses_suppression_list(email: str) -> bool:
    """
    Add an email to the SES account suppression list.

    :param email: The email address to suppress
    :return: True if the email was added, False on failure
    """
    if settings.DISABLE_EMAILS:
        return False

    try:
        import boto3

        client = boto3.client('sesv2', region_name=settings.AWS_REGION)
        client.put_suppressed_destination(
            EmailAddress=email,
            Reason='BOUNCE',
        )
        logger.info(f'Added {redact_email(email)} to SES suppression list')
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
    msg.attach_alternative(html_content, "text/html")

    extra_tags = [f"type:{email_type}"] if email_type else []

    try:
        msg.send()
        logger.debug(f"Sent email successfully to {len(to)} recipient(s)")
        metricutils.increment('action.email.sent', extra_tags=extra_tags)
    except smtplib.SMTPRecipientsRefused as e:
        logger.warning(f"Recipients refused by SES: {e.recipients}")
        metricutils.increment('action.email.failed', extra_tags=extra_tags)
        for rejected_email in e.recipients:
            add_to_ses_suppression_list(rejected_email)
        raise EmailSuppressedException(to, original_error=e) from e
    except Exception:
        logger.error("Failed to send email", exc_info=True)
        metricutils.increment('action.email.failed', extra_tags=extra_tags)
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
