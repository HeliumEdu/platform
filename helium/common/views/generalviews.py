import logging

from django.conf import settings
from django.shortcuts import render, redirect

from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def home(request):
    metricutils.increment(request, 'view.home')

    return render(request, "home.html")


def support(request):
    metricutils.increment(request, 'view.support')

    return redirect(settings.SUPPORT_REDIRECT_URL)


def terms(request):
    metricutils.increment(request, 'view.terms')

    return render(request, "terms.html")


def privacy(request):
    metricutils.increment(request, 'view.privacy')

    return render(request, "privacy.html")


def press(request):
    metricutils.increment(request, 'view.press')

    return render(request, "press.html")


def about(request):
    metricutils.increment(request, 'view.about')

    return render(request, "about.html")


def contact(request):
    metricutils.increment(request, 'view.contact')

    return render(request, "contact.html")
