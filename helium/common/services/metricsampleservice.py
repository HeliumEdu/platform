import logging
import math

from django.utils import timezone

from helium.common.utils import metricutils
from helium.common.models import MetricSample

logger = logging.getLogger(__name__)


def record_gauge(metric, value, extra_tags=None):
    """
    Emit a nightly gauge to Datadog, and keep today's value as a `MetricSample` so its history outlives
    Datadog's retention.

    :param metric: The metric name, without the `platform.` prefix Datadog adds.
    :param value: The value to record.
    :param extra_tags: `key:value` tags qualifying the value.
    """
    _store(metric, extra_tags, value)
    metricutils.gauge(metric, value, extra_tags=extra_tags)


def record_distribution(metric, values, extra_tags=None):
    """
    Emit every sample of a nightly distribution to Datadog, and keep today's summary as `MetricSample`s.

    :param metric: The metric name, without the `platform.` prefix Datadog adds.
    :param values: One sample per entity.
    :param extra_tags: `key:value` tags qualifying the samples.
    """
    for value in values:
        metricutils.distribution(metric, value, extra_tags=extra_tags)

    store_summary(metric, values, extra_tags=extra_tags)


def store_summary(metric, values, extra_tags=None):
    """
    Keep today's `count`, `avg` and `p95` of `values` as `MetricSample`s, each tagged with its `stat`. Nothing is
    stored when there are no values.

    :param metric: The metric name.
    :param values: The samples to summarize.
    :param extra_tags: `key:value` tags qualifying the samples.
    """
    if not values:
        return

    ordered = sorted(values)
    tags = list(extra_tags or [])
    _store(metric, [*tags, 'stat:count'], len(ordered))
    _store(metric, [*tags, 'stat:avg'], sum(ordered) / len(ordered))
    _store(metric, [*tags, 'stat:p95'], ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)])


def _store(metric, tags, value):
    MetricSample.objects.update_or_create(recorded_on=timezone.now().date(), metric=metric,
                                          dimension=','.join(tags or []), defaults={'value': value})
