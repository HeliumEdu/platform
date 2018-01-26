import logging

from django.conf import settings
from django.shortcuts import render, redirect

from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def home(request):
    metricutils.increment('view.home', request)

    return render(request, "home.html")


def support(request):
    metricutils.increment('view.support', request)

    return redirect(settings.SUPPORT_REDIRECT_URL)


def terms(request):
    metricutils.increment('view.terms', request)

    return render(request, "terms.html")


def privacy(request):
    metricutils.increment('view.privacy', request)

    return render(request, "privacy.html")


def press(request):
    metricutils.increment('view.press', request)

    return render(request, "press.html")


def about(request):
    metricutils.increment('view.about', request)

    return render(request, "about.html")


def contact(request):
    metricutils.increment('view.contact', request)

    return render(request, "contact.html")
