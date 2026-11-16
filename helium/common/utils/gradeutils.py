import copy
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional, Set, Tuple

from helium.common import enums
from helium.common.timezones import COUNTRY_BY_TIME_ZONE

_AT_RISK_THRESHOLD_OVERRIDES_BY_COUNTRY = {
    **dict.fromkeys(['GB', 'IE', 'IN', 'PK', 'BD'], 50),
    **dict.fromkeys(['AU', 'NZ', 'SG', 'MY', 'ZA', 'HK', 'FR', 'BE', 'NL', 'DE', 'AT', 'ES', 'PT', 'FI'], 60),
}


def at_risk_threshold_for_time_zone(time_zone):
    """
    The at-risk grade threshold the passing conventions of a time zone's country call for, set one band above the
    pass mark so a passing grade is not flagged. The time zone is the only regional signal the platform holds.

    :param time_zone: An IANA time zone name, e.g. "Europe/Berlin".
    :return: The threshold percentage, or None if the country has no convention that differs from the default.
    """
    return _AT_RISK_THRESHOLD_OVERRIDES_BY_COUNTRY.get(COUNTRY_BY_TIME_ZONE.get(time_zone))


def preset_grade_scale(template):
    """
    :param template: A `GRADE_SCALE_TEMPLATES` id.
    :return: A copy of that preset's grade scale.
    """
    return copy.deepcopy(enums.GRADE_SCALE_TEMPLATES[template]['scale'])


def preset_for(grade_scale):
    """
    :param grade_scale: A list of bands.
    :return: The `GRADE_SCALE_TEMPLATES` id whose scale matches, or None for a custom scale.
    """
    return next((template for template, preset in enums.GRADE_SCALE_TEMPLATES.items()
                 if preset['scale'] == grade_scale), None)


def is_compatible_preset(template: int, grade_scale: List[dict]) -> bool:
    """
    Whether a class in a group with `grade_scale` can use the `template` preset: every grade the preset awards (its
    grade point and label) is one the group's scale awards too, so the class grades on the group's scale with its own
    cutoffs, and the group's GPA stays on one scale.

    :param template: A `GRADE_SCALE_TEMPLATES` id.
    :param grade_scale: The group's bands, or empty for no grade scale.
    :return: True if the class can use the preset.
    """
    if not grade_scale or template not in enums.GRADE_SCALE_TEMPLATES or template == enums.GRADE_SCALE_NONE:
        return False

    return _grades_awarded(enums.GRADE_SCALE_TEMPLATES[template]['scale']) <= _grades_awarded(grade_scale)


def compatible_presets(grade_scale: List[dict]) -> List[int]:
    """
    :param grade_scale: The group's bands, or empty for no grade scale.
    :return: The `GRADE_SCALE_TEMPLATES` ids a class in the group can use.
    """
    return [template for template in enums.GRADE_SCALE_TEMPLATES if is_compatible_preset(template, grade_scale)]


def effective_grade_scale(template: Optional[int], group_grade_scale: List[dict]) -> List[dict]:
    """
    :param template: The class's `grade_scale_template`, or None to use the group's scale.
    :param group_grade_scale: The group's bands, or empty for no grade scale.
    :return: The bands that turn the class's grade into its grade point.
    """
    if template is None or not group_grade_scale:
        return group_grade_scale

    return preset_grade_scale(template)


def format_grade_percent(grade: str, number_format: int) -> str:
    """
    A grade as the app shows it: a percent with two decimals in the user's number format (e.g. "1,234.50%", or
    "1.234,50%" with a comma). Mirrors the app's `GradeHelper.gradeForDisplay`.

    :param grade: The grade, as "earned/possible".
    :param number_format: The user's `number_format`.
    :return: The formatted grade, or an empty string when it's ungraded.
    """
    earned, _, possible = grade.partition('/')
    if grade == enums.UNGRADED or not possible:
        return ''

    percent = (Decimal(earned) / Decimal(possible) * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    formatted = f'{percent:,.2f}'
    if number_format == enums.COMMA:
        formatted = formatted.translate(str.maketrans(',.', '.,'))

    return f'{formatted}%'


def _grades_awarded(grade_scale: List[dict]) -> Set[Tuple[float, str]]:
    return {(round(float(band['grade_point']), 2), band['label']) for band in grade_scale}


def default_grade_scale():
    """
    :return: No grade scale.
    """
    return preset_grade_scale(enums.GRADE_SCALE_NONE)
