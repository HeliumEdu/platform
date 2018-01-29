from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


class HeliumError(Exception):
    pass


def send_multipart_email(template_name, context, subject, to):
    """
    Send a multipart text/html email.

    :param template_name: The path to the template (without extension), assuming both a .txt and .html version are present
    :param context: A dictionary of context elements to pass to the email templates
    :param subject: The subject of the email
    :param to: A list of email addresses to which to send
    :return:
    """
    plaintext = get_template('{}.txt'.format(template_name))
    html = get_template('{}.html'.format(template_name))
    text_content = plaintext.render(context)
    html_content = html.render(context)

    msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()


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
