__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.http import JsonResponse


def handler_404(request, exception):
    return JsonResponse({"detail": "Route not found."}, status=404)


def handler_500(request):
    return JsonResponse({"detail": "Internal server error."}, status=500)
