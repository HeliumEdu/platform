from django.http import JsonResponse

from helium.common import errorcodes
from helium.common.handlers.exceptions import detail_body


def handler_400(request, exception):
    return JsonResponse(detail_body(request, "Bad request.", errorcodes.BAD_REQUEST), status=400)


def handler_403(request, exception):
    return JsonResponse(detail_body(request, "Permission denied.", errorcodes.PERMISSION_DENIED), status=403)


def handler_404(request, exception):
    return JsonResponse(detail_body(request, "Route not found.", errorcodes.NOT_FOUND), status=404)


def handler_500(request):
    return JsonResponse(detail_body(request, "Internal server error.", errorcodes.SERVER_ERROR), status=500)
