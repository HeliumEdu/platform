from datetime import date, datetime, timezone as dt_timezone
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from helium.common.models import MetricSample
from helium.common.services import metricsampleservice


class TestCaseMetricSampleService(TestCase):
    @mock.patch('helium.common.services.metricsampleservice.metricutils.gauge')
    def test_record_gauge_stores_and_emits(self, mock_gauge):
        # WHEN
        metricsampleservice.record_gauge('users.active', 42, extra_tags=['window:30d', 'staff:false'])

        # THEN
        mock_gauge.assert_called_once_with('users.active', 42, extra_tags=['window:30d', 'staff:false'])
        sample = MetricSample.objects.get(metric='users.active')
        self.assertEqual(sample.recorded_on, timezone.now().date())
        self.assertEqual(sample.dimension, 'window:30d,staff:false')
        self.assertEqual(sample.value, 42)

    @mock.patch('helium.common.services.metricsampleservice.metricutils.gauge')
    def test_record_gauge_same_day_overwrites(self, mock_gauge):
        # GIVEN
        metricsampleservice.record_gauge('users.active', 42, extra_tags=['window:30d'])

        # WHEN
        metricsampleservice.record_gauge('users.active', 50, extra_tags=['window:30d'])

        # THEN
        self.assertEqual(list(MetricSample.objects.filter(metric='users.active').values_list('value', flat=True)),
                         [50])

    @mock.patch('helium.common.services.metricsampleservice.metricutils.distribution')
    def test_record_distribution_emits_every_sample_and_stores_summary(self, mock_distribution):
        # GIVEN
        values = list(range(1, 21))

        # WHEN
        metricsampleservice.record_distribution('users.data.homework_per_user', values, extra_tags=['staff:false'])

        # THEN
        self.assertEqual(mock_distribution.call_count, 20)
        stored = dict(MetricSample.objects.filter(metric='users.data.homework_per_user')
                      .values_list('dimension', 'value'))
        self.assertEqual(stored, {'staff:false,stat:count': 20, 'staff:false,stat:avg': 10.5,
                                  'staff:false,stat:p95': 19})

    def test_store_summary_without_values_stores_nothing(self):
        # WHEN
        metricsampleservice.store_summary('users.mobile_app_usage_percent', [], extra_tags=['window:30d'])

        # THEN
        self.assertFalse(MetricSample.objects.filter(metric='users.mobile_app_usage_percent').exists())

    @mock.patch('helium.common.services.metricsampleservice.metricutils.gauge')
    def test_recorded_on_is_the_utc_date(self, mock_gauge):
        for zone in ('Pacific/Auckland', 'America/Los_Angeles'):
            with self.subTest(zone=zone):
                # GIVEN
                MetricSample.objects.all().delete()
                late_utc = datetime(2026, 10, 9, 23, 30, tzinfo=dt_timezone.utc)

                # WHEN
                with timezone.override(zone), mock.patch('django.utils.timezone.now', return_value=late_utc):
                    metricsampleservice.record_gauge('users.active', 1)

                # THEN
                self.assertEqual(MetricSample.objects.get(metric='users.active').recorded_on, date(2026, 10, 9))
