__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import math
import re
import secrets
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count


def is_admin_allowed_email(email):
    """
    Return True if the email's domain is in ADMIN_ALLOWED_DOMAINS. Security boundary — governs
    who can be promoted to superuser. Not the right predicate for filtering internal staff out
    of analytics/metrics; use `is_staff_user` for that.
    """
    domain = email.split('@')[-1].lower() if '@' in email else ''
    return domain in settings.ADMIN_ALLOWED_DOMAINS


def is_staff_email(email):
    """
    Return True if the email belongs to a staff domain. Matches the frontend's `setStaffStatus`
    filter. Use when a User object isn't available (e.g. bounce handling with just an address).
    """
    lowered = (email or '').lower()
    domain = lowered.split('@')[-1] if '@' in lowered else ''
    return domain == 'heliumedu.com' or domain.endswith('.heliumedu.com') or \
           domain == 'heliumedu.dev' or domain.endswith('.heliumedu.dev')


def is_staff_user(user):
    """
    Return True if the user is internal staff — superuser or has a staff email domain. Matches
    the admin-area `staff_filter` predicate, so the same users are excluded from analytics and
    metrics across the stack.
    """
    if user is None:
        return False
    if user.is_superuser:
        return True
    return is_staff_email(user.email)


def generate_verification_code():
    return secrets.randbelow(900000) + 100000


def rollup_power_users(UserModel, staff_filter):
    """
    Tag the top 5% of 30-day active non-staff users as power users based on a composite
    percentile score across homework depth, recent completions, and note-taking. Clears the
    flag for users who drop out of the top 5%. Requires at least 20 active non-staff users
    to tag anyone.

    :param UserModel: The active user model class.
    :param staff_filter: A Q object matching staff/superuser accounts to exclude.
    :return: Tuple of (promoted_count, cleared_count).
    """
    from helium.planner.models import Course, Homework, Note

    cutoff_30d = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=30)
    cutoff_14d = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=14)

    user_ids = list(
        UserModel.objects.filter(is_active=True, last_activity__gte=cutoff_30d)
                         .filter(~staff_filter)
                         .values_list('pk', flat=True)
    )
    total_users = len(user_ids)

    power_user_ids = set()

    if total_users >= 20:
        course_qs = Course.objects.filter(
            course_group__user__in=user_ids,
            course_group__example_schedule=False,
        )
        hw_qs = Homework.objects.filter(
            course__in=course_qs,
            course__course_group__example_schedule=False,
        )

        hw_counts = dict(
            hw_qs.values('course__course_group__user_id')
                 .annotate(c=Count('pk'))
                 .values_list('course__course_group__user_id', 'c')
        )
        completion_counts = dict(
            hw_qs.filter(completed=True, completed_at__gte=cutoff_14d)
                 .values('course__course_group__user_id')
                 .annotate(c=Count('pk'))
                 .values_list('course__course_group__user_id', 'c')
        )
        note_counts = dict(
            Note.objects.filter(user__in=user_ids, example_schedule=False)
                        .values('user_id')
                        .annotate(c=Count('pk'))
                        .values_list('user_id', 'c')
        )

        def _percentile_ranks(counts):
            sorted_ids = sorted(user_ids, key=lambda u: counts.get(u, 0))
            return {uid: i / (total_users - 1) for i, uid in enumerate(sorted_ids)}

        hw_ranks = _percentile_ranks(hw_counts)
        completion_ranks = _percentile_ranks(completion_counts)
        note_ranks = _percentile_ranks(note_counts)

        sorted_by_composite = sorted(
            user_ids,
            key=lambda uid: hw_ranks[uid] + completion_ranks[uid] + note_ranks[uid],
        )
        threshold_idx = math.ceil(total_users * 0.95)
        power_user_ids = set(sorted_by_composite[threshold_idx:])

    cleared = UserModel.objects.filter(is_power_user=True).exclude(pk__in=power_user_ids).update(is_power_user=False)
    promoted = UserModel.objects.filter(pk__in=power_user_ids, is_power_user=False).update(is_power_user=True)

    return promoted, cleared


def generate_unique_username_from_email(email):
    """
    Generate a unique username from an email local-part, appending a counter on collisions.
    """
    UserModel = get_user_model()

    max_length = UserModel._meta.get_field('username').max_length

    local_part = (email or '').split('@', 1)[0].strip().lower()
    base_username = re.sub(r'[^\w.+-]', '', local_part) or 'user'
    base_username = base_username[:max_length]

    username = base_username
    counter = 1

    while UserModel.objects.filter(username=username).exists():
        suffix = str(counter)
        truncated_base = base_username[:max_length - len(suffix)]
        username = f'{truncated_base}{suffix}'
        counter += 1

    return username
