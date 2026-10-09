import logging

from django.db import models

logger = logging.getLogger(__name__)


class MetricSample(models.Model):
    """
    One recorded value of a platform metric, kept so its history outlives external retention (Datadog) and
    can be re-plotted later. Values are aggregates: nothing here identifies a user.
    """

    recorded_on = models.DateField(help_text='The UTC date the value applies to.')

    metric = models.CharField(help_text='The metric the value belongs to, e.g. `users.cumulative`.', max_length=255)

    dimension = models.CharField(help_text='Comma-separated `key:value` pairs qualifying the value, e.g. '
                                           '`milestone:30d,staff:false`.',
                                 max_length=255)

    value = models.FloatField(help_text='The recorded value.', default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('recorded_on', 'metric', 'dimension')
        constraints = [
            models.UniqueConstraint(fields=('recorded_on', 'metric', 'dimension'), name='unique_metric_sample'),
        ]

    def __str__(self):  # pragma: no cover
        return f'{self.recorded_on} {self.metric} [{self.dimension}] = {self.value}'
