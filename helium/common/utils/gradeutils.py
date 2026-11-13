import copy

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


def default_grade_scale():
    """
    :return: No grade scale.
    """
    return preset_grade_scale(enums.GRADE_SCALE_NONE)
