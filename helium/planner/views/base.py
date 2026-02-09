__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from datetime import timezone

from dateutil import parser
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin

from helium.common.views.base import HeliumAPIView


class HeliumCalendarItemAPIView(HeliumAPIView, ListModelMixin):
    def filter_queryset(self, queryset):
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)

        _from = self.request.query_params.get('from', None)
        to = self.request.query_params.get('to', None)
        if _from and to:
            _from = parser.parse(_from).astimezone(timezone.utc)
            to = parser.parse(to).astimezone(timezone.utc)
            queryset = queryset.filter(Q(start__range=(_from, to)) |
                                       Q(end__range=(_from, to)) |
                                       # Also include results where start/end dates are wider than the window
                                       Q(start__lte=_from, end__gte=to))

        return queryset

    def get(self, request, *args, **kwargs):
        _from = request.query_params.get('from')
        to = request.query_params.get('to')

        if (_from and not to) or (to and not _from):
            raise ValidationError(
                detail="Both 'from' and 'to' must be provided together.",
                code=status.HTTP_400_BAD_REQUEST
            )

        return self.list(request, *args, **kwargs)
