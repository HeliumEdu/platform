__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework.generics import GenericAPIView

from django.conf import settings

from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


class HeliumAPIView(GenericAPIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__request_metrics = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        if settings.SENTRY_ENABLED and request.user and request.user.is_authenticated:
            import sentry_sdk
            sentry_sdk.set_user({"id": request.user.id})

        self.__request_metrics = metricutils.request_start(request)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if self.__request_metrics:
            metricutils.request_stop(self.__request_metrics, request, response)

        return response
