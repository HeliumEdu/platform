__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.http import JsonResponse


def handler_400(request, exception):
    return JsonResponse({"detail": "Bad request."}, status=400)


def handler_403(request, exception):
    return JsonResponse({"detail": "Permission denied."}, status=403)


def handler_404(request, exception):
    return JsonResponse({"detail": "Route not found."}, status=404)


def handler_500(request):
    return JsonResponse({"detail": "Internal server error."}, status=500)
