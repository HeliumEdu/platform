__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.19"

import logging

from rest_framework.generics import GenericAPIView

from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


class HeliumAPIView(GenericAPIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__request_metrics = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        self.__request_metrics = metricutils.request_start(request)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if self.__request_metrics:
            metricutils.request_stop(self.__request_metrics, request, response)

        return response
