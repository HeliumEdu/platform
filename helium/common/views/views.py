import logging

from rest_framework.generics import GenericAPIView

from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.3'

logger = logging.getLogger(__name__)


class HeliumAPIView(GenericAPIView):
    def __init__(self, **kwargs):
        super(HeliumAPIView, self).__init__(**kwargs)

        self.__request_metrics = None

    def initial(self, request, *args, **kwargs):
        super(HeliumAPIView, self).initial(request, *args, **kwargs)

        self.__request_metrics = metricutils.request_start(request)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super(HeliumAPIView, self).finalize_response(request, response, *args, **kwargs)

        # TODO: responses should have a Request-Cached-Response header set

        if self.__request_metrics:
            metricutils.request_stop(self.__request_metrics, response)

        return response
