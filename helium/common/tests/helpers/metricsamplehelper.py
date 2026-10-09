from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from helium.auth.tests.helpers import userhelper
from helium.common.models import MetricSample
from helium.common.services import cumulativeuserservice


def given_total_users_seed(value):
    MetricSample.objects.update_or_create(metric=cumulativeuserservice.TOTAL_USERS_SEED_METRIC, dimension='',
                                          defaults={'recorded_on': timezone.now().date(), 'value': value})


def given_a_user_with_tenure(username, email, created_days_ago, active_days_after_created, time_zone=None,
                             now=None):
    user = userhelper.given_a_user_exists(username=username, email=email, time_zone=time_zone)
    created_at = (now or timezone.now()) - timedelta(days=created_days_ago)
    get_user_model().objects.filter(pk=user.pk).update(
        created_at=created_at, last_activity=created_at + timedelta(days=active_days_after_created))
    user.refresh_from_db()
    return user


def verify_cumulative_users(test_case, mock_gauge, expected):
    emitted = {call.kwargs['extra_tags'][0].removeprefix('milestone:'): call.args[1]
               for call in mock_gauge.call_args_list if call.args[0] == cumulativeuserservice.CUMULATIVE_USERS_METRIC}
    test_case.assertEqual(emitted, expected)

    stored = dict(MetricSample.objects.filter(
        metric=cumulativeuserservice.CUMULATIVE_USERS_METRIC, recorded_on=timezone.now().date(),
    ).values_list('dimension', 'value'))
    test_case.assertEqual(stored, {f'milestone:{milestone}': value for milestone, value in expected.items()})
