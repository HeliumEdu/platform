import logging

from django.contrib.auth.decorators import login_required

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

logger = logging.getLogger(__name__)


@login_required
def importexport_import(request):
    # TODO: implement
    raise NotImplementedError


@login_required
def importexport_export(request):
    # TODO: implement
    raise NotImplementedError
