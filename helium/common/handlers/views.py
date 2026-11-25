from django.http import JsonResponse
from django.utils.translation import gettext

from helium.common import errorcodes
from helium.common.handlers.exceptions import detail_body


def handler_400(request, exception):
    return JsonResponse(detail_body(request, gettext("Bad request."), errorcodes.BAD_REQUEST), status=400)


def handler_403(request, exception):
    return JsonResponse(detail_body(request, gettext("Permission denied."), errorcodes.PERMISSION_DENIED), status=403)


def handler_404(request, exception):
    return JsonResponse(detail_body(request, gettext("Route not found."), errorcodes.NOT_FOUND), status=404)


def handler_500(request):
    return JsonResponse(detail_body(request, gettext("Server error. Please try again later."), errorcodes.SERVER_ERROR),
                        status=500)
