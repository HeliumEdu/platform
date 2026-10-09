import logging
from collections import Counter
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import F, Q, Sum
from django.utils import timezone

from helium.auth.utils.userutils import is_staff_user
from helium.common.models import MetricSample
from helium.common.services import metricsampleservice

logger = logging.getLogger(__name__)

CUMULATIVE_USERS_METRIC = 'users.cumulative'

DELETED_USERS_METRIC = 'users.deleted'

TOTAL_USERS_SEED_METRIC = 'users.registered.seed'

TOTAL_USERS_DELETED_METRIC = 'users.total.deleted'


def record_deleted_user(user):
    """
    Add a just-deleted user to the day's anonymous deletion tally, so cumulative user counts keep including
    them once their row is gone. Only the tally is stored, nothing that identifies the user. Unverified and
    staff accounts are not tallied, since cumulative counts never include them.

    :param user: The user whose row was just deleted.
    """
    if not user.is_active or is_staff_user(user):
        return

    _increment(DELETED_USERS_METRIC, f'span_days:{_span_days(user.created_at, user.last_activity)}')
    if user.pk > _total_users_seed():
        _increment(TOTAL_USERS_DELETED_METRIC, '')


def record_cumulative_users():
    """
    Record today's cumulative user counts, and emit each to Datadog. Staff accounts are only counted within the
    `total` seed.

    - `total`: every account when tracking began (the highest user ID then, staff and unverified included),
      plus each verified, non-staff user created since.
    - `verified`: users who completed verification.
    - `tourists`: verified users who stopped using Helium within the smallest `USER_TENURE_MILESTONE_DAYS`.
    - one per `USER_TENURE_MILESTONE_DAYS`, e.g. `30d`: verified users whose last activity is at least that
      many days after their account was created.

    Users still in the table are counted from it; deleted users from their anonymous tallies, so a user stays
    counted after their account is deleted.
    """
    UserModel = get_user_model()

    verified = UserModel.objects.filter(is_active=True).exclude(
        pk__in=UserModel.objects.staff().values('pk'))
    seed = _total_users_seed()
    deleted_since_seed = MetricSample.objects.filter(metric=TOTAL_USERS_DELETED_METRIC).aggregate(
        total=Sum('value'))['total'] or 0
    spans = _deleted_spans()
    tourist_days = min(settings.USER_TENURE_MILESTONE_DAYS)
    tourist_cutoff = timezone.now() - timedelta(days=tourist_days)

    counts = {
        'total': seed + verified.filter(pk__gt=seed).count() + deleted_since_seed,
        'verified': verified.count() + sum(spans.values()),
        'tourists': (verified.filter(created_at__lte=tourist_cutoff).exclude(_reached(tourist_days)).count()
                     + sum(count for span, count in spans.items() if span < tourist_days)),
    }
    for days in settings.USER_TENURE_MILESTONE_DAYS:
        counts[f'{days}d'] = (verified.filter(_reached(days)).count()
                              + sum(count for span, count in spans.items() if span >= days))

    for milestone, value in counts.items():
        _record_cumulative(milestone, value)


def _reached(days):
    return Q(last_activity__gte=F('created_at') + timedelta(days=days))


def _span_days(created_at, last_activity):
    return max(0, (last_activity - created_at).days)


def _total_users_seed():
    sample = MetricSample.objects.filter(metric=TOTAL_USERS_SEED_METRIC).first()
    return sample.value if sample else 0


def _deleted_spans():
    spans = Counter()
    for dimension, value in MetricSample.objects.filter(metric=DELETED_USERS_METRIC).values_list('dimension', 'value'):
        spans[int(dimension.removeprefix('span_days:'))] += value

    return spans


def _increment(metric, dimension):
    sample, _ = MetricSample.objects.get_or_create(recorded_on=timezone.now().date(), metric=metric,
                                                   dimension=dimension)
    MetricSample.objects.filter(pk=sample.pk).update(value=F('value') + 1)


def _record_cumulative(milestone, value):
    metricsampleservice.record_gauge(CUMULATIVE_USERS_METRIC, value, extra_tags=[f'milestone:{milestone}'])
