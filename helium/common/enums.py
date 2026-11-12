from helium.common.timezones import TIME_ZONE_CHOICES  # noqa: F401

PYTHON_TO_HELIUM_DAY_OF_WEEK = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 0}
WEEKDAY_TO_ICAL = {0: 'MO', 1: 'TU', 2: 'WE', 3: 'TH', 4: 'FR', 5: 'SA', 6: 'SU'}
RECURRENCE_HORIZON_YEARS = 5

MONTH = 0
WEEK = 1
DAY = 2
LIST = 3
AGENDA_WEEK = 4
THREE_DAY = 5
VIEW_CHOICES = (
    (MONTH, 'Month'),
    (WEEK, 'Week'),
    (THREE_DAY, '3-Day'),
    (DAY, 'Day'),
    (LIST, 'List'),
    (AGENDA_WEEK, 'Agenda')
)

SUNDAY = 0
MONDAY = 1
TUESDAY = 2
WEDNESDAY = 3
THURSDAY = 4
FRIDAY = 5
SATURDAY = 6
DAY_OF_WEEK_CHOICES = (
    (SUNDAY, 'Sunday'),
    (MONDAY, 'Monday'),
    (TUESDAY, 'Tuesday'),
    (WEDNESDAY, 'Wednesday'),
    (THURSDAY, 'Thursday'),
    (FRIDAY, 'Friday'),
    (SATURDAY, 'Saturday')
)

EMAIL = 1
PUSH = 3
REMINDER_TYPE_CHOICES = (
    (EMAIL, 'Email'),
    (PUSH, 'Push'),
)

MINUTES = 0
HOURS = 1
DAYS = 2
WEEKS = 3
REMINDER_OFFSET_TYPE_CHOICES = (
    (MINUTES, 'minutes'),
    (HOURS, 'hours'),
    (DAYS, 'days'),
    (WEEKS, 'weeks')
)

PREFERRED_COLORS = (
    "#EC6F92", "#E74674", "#E21D55",
    "#B91846", "#901336", "#5E0C23",
    "#DC7D50", "#D5602A", "#AF4F23",
    "#7B3718", "#622C13", "#3C1B0C",
    "#CFA25E", "#C48D3B", "#A17430",
    "#7E5A26", "#5A411B", "#372810",
    "#33FABE", "#06F9B0", "#05CC90",
    "#049F71", "#037251", "#024B35",
    "#5658D7", "#3033CF", "#282AA9",
    "#1F2184", "#16175F", "#0D0E38",
    "#C964B5", "#BD42A4", "#9B3687",
    "#792A69", "#571E4C", "#3C1534",
    "#C09BC0", "#AE7EAE", "#9D629D",
    "#815181", "#643F64", "#553555"
)

OWNED = 0
RENTED = 1
ORDERED = 2
SHIPPED = 3
NEED = 4
RECEIVED = 5
TO_SELL = 6
DIGITAL = 7
RESOURCE_STATUS_CHOICES = (
    (OWNED, 'Owned'),
    (RENTED, 'Rented'),
    (ORDERED, 'Ordered'),
    (SHIPPED, 'Shipped'),
    (NEED, 'Needed'),
    (RECEIVED, 'Received'),
    (TO_SELL, 'To Sell'),
    (DIGITAL, 'Digital')
)

BRAND_NEW = 0
REFURBISHED = 1
USED_LIKE_NEW = 2
USED_VERY_GOOD = 3
USED_GOOD = 4
USED_ACCEPTABLE = 5
USED_POOR = 6
BROKEN = 7
DIGITAL = 8
CONDITION_CHOICES = (
    (BRAND_NEW, 'Brand New'),
    (REFURBISHED, 'Refurbished'),
    (USED_LIKE_NEW, 'Used - Like New'),
    (USED_VERY_GOOD, 'Used - Very Good'),
    (USED_GOOD, 'Used - Good'),
    (USED_ACCEPTABLE, 'Used - Acceptable'),
    (USED_POOR, 'Used - Poor'),
    (BROKEN, 'Broken'),
    (DIGITAL, 'Digital')
)

EVENT = 0
HOMEWORK = 1
EXTERNAL = 2
COURSE = 3
CALENDAR_ITEM_TYPE_CHOICES = (
    (EVENT, 'Event'),
    (HOMEWORK, 'Homework'),
    (EXTERNAL, 'External'),
    (COURSE, 'Class')
)

MDY = 0
DMY = 1
DATE_FORMAT_CHOICES = (
    (MDY, 'Month/Day/Year'),
    (DMY, 'Day/Month/Year'),
)

TWELVE_HOUR = 0
TWENTY_FOUR_HOUR = 1
TIME_FORMAT_CHOICES = (
    (TWELVE_HOUR, '12-hour'),
    (TWENTY_FOUR_HOUR, '24-hour'),
)

POINT = 0
COMMA = 1
NUMBER_FORMAT_CHOICES = (
    (POINT, 'Point'),
    (COMMA, 'Comma'),
)

SETUP_PENDING = 0
SETUP_IMPORTING = 1
SETUP_COMPLETE = 2
SETUP_STATE_CHOICES = (
    (SETUP_PENDING, 'Pending'),
    (SETUP_IMPORTING, 'Importing'),
    (SETUP_COMPLETE, 'Complete'),
)

LIGHT = 0
DARK = 1
SYSTEM = 2
COLOR_SCHEME_THEME = (
    (LIGHT, 'Light'),
    (DARK, 'Dark'),
    (SYSTEM, 'System'),
)

STANDARD = 0
CATEGORY_TEMPLATE_CHOICES = (
    (STANDARD, 'Standard'),
)

CATEGORY_TEMPLATES = {
    STANDARD: (
        {'title': 'Homework 👨🏽‍💻', 'color': '#E21D55'},
        {'title': 'Final Exam 📈', 'color': '#AF4F23'},
        {'title': 'Midterm 📈', 'color': '#A17430'},
        {'title': 'Project 🔨', 'color': '#05CC90'},
        {'title': 'Quiz 💡', 'color': '#0D0E38'},
        {'title': 'Reading 📖', 'color': '#3C1534'},
        {'title': 'Lab 🧪', 'color': '#553555'},
    ),
}

WEEKLY = 0
AB_DAY = 1
SIX_DAY_CYCLE = 2
EIGHT_DAY_CYCLE = 3
WEEK_AB = 4
SEVEN_DAY_CYCLE = 5
TEN_DAY_CYCLE = 6
SCHEDULE_TEMPLATES = {
    WEEKLY: {'label': 'Weekly', 'fields': {}},
    AB_DAY: {'label': 'A/B Day', 'fields': {'cycle_length': 2}},
    SIX_DAY_CYCLE: {'label': '6-Day Cycle', 'fields': {'cycle_length': 6}},
    SEVEN_DAY_CYCLE: {'label': '7-Day Cycle', 'fields': {'cycle_length': 7}},
    EIGHT_DAY_CYCLE: {'label': '8-Day Cycle', 'fields': {'cycle_length': 8}},
    TEN_DAY_CYCLE: {'label': '10-Day Cycle', 'fields': {'cycle_length': 10}},
    WEEK_AB: {'label': 'Week A/B', 'fields': {'is_week_based': True}},
}
SCHEDULE_TEMPLATE_CHOICES = tuple((key, template['label']) for key, template in SCHEDULE_TEMPLATES.items())


UNGRADED = '-1/100'
NO_GRADE = -1


def _grade_scale(*bands):
    return [{'min_grade': float(min_grade), 'grade_point': float(grade_point), 'label': label}
            for min_grade, grade_point, label in bands]


GRADE_SCALE_NONE = 0
GRADE_SCALE_4_0 = 1
GRADE_SCALE_4_0_PLUS_MINUS = 2
GRADE_SCALE_4_33_PLUS_MINUS = 3
GRADE_SCALE_4_5 = 4
GRADE_SCALE_7_0 = 5
GRADE_SCALE_9_0 = 6
GRADE_SCALE_10_0 = 7
GRADE_SCALE_1_5_PASS_50 = 8
GRADE_SCALE_1_5_PASS_75 = 9
GRADE_SCALE_TEMPLATES = {
    GRADE_SCALE_NONE: {'label': 'None', 'scale': []},
    GRADE_SCALE_4_0: {'label': '4.0', 'scale': _grade_scale(
        (0, 0, 'F'), (60, 1, 'D'), (70, 2, 'C'), (80, 3, 'B'), (90, 4, 'A'))},
    GRADE_SCALE_4_0_PLUS_MINUS: {'label': '4.0 with +/-', 'scale': _grade_scale(
        (0, 0, 'F'), (60, 0.7, 'D-'), (63, 1, 'D'), (67, 1.3, 'D+'), (70, 1.7, 'C-'), (73, 2, 'C'), (77, 2.3, 'C+'),
        (80, 2.7, 'B-'), (83, 3, 'B'), (87, 3.3, 'B+'), (90, 3.7, 'A-'), (93, 4, 'A'), (97, 4, 'A+'))},
    GRADE_SCALE_4_33_PLUS_MINUS: {'label': '4.33 with +/-', 'scale': _grade_scale(
        (0, 0, 'F'), (60, 0.7, 'D-'), (63, 1, 'D'), (67, 1.3, 'D+'), (70, 1.7, 'C-'), (73, 2, 'C'), (77, 2.3, 'C+'),
        (80, 2.7, 'B-'), (83, 3, 'B'), (87, 3.3, 'B+'), (90, 3.7, 'A-'), (93, 4, 'A'), (97, 4.33, 'A+'))},
    GRADE_SCALE_4_5: {'label': '4.5', 'scale': _grade_scale(
        (0, 0, 'F'), (60, 1, 'D'), (65, 1.5, 'D+'), (70, 2, 'C'), (75, 2.5, 'C+'), (80, 3, 'B'), (85, 3.5, 'B+'),
        (90, 4, 'A'), (95, 4.5, 'A+'))},
    GRADE_SCALE_7_0: {'label': '7.0', 'scale': _grade_scale(
        (0, 0, 'F'), (50, 4, 'P'), (65, 5, 'C'), (75, 6, 'D'), (85, 7, 'HD'))},
    GRADE_SCALE_9_0: {'label': '9.0', 'scale': _grade_scale(
        (0, 0, 'D'), (50, 1, 'C-'), (55, 2, 'C'), (60, 3, 'C+'), (65, 4, 'B-'), (70, 5, 'B'), (75, 6, 'B+'),
        (80, 7, 'A-'), (85, 8, 'A'), (90, 9, 'A+'))},
    GRADE_SCALE_10_0: {'label': '10.0', 'scale': _grade_scale(
        (0, 0, 'F'), (40, 4, 'P'), (45, 5, 'C'), (50, 6, 'B'), (60, 7, 'B+'), (70, 8, 'A'), (80, 9, 'A+'),
        (90, 10, 'O'))},
    GRADE_SCALE_1_5_PASS_50: {'label': '1.0-5.0 (pass at 50%)', 'scale': _grade_scale(
        (0, 5, ''), (50, 4, ''), (55, 3.7, ''), (60, 3.3, ''), (65, 3, ''), (70, 2.7, ''), (75, 2.3, ''), (80, 2, ''),
        (85, 1.7, ''), (90, 1.3, ''), (95, 1, ''))},
    GRADE_SCALE_1_5_PASS_75: {'label': '1.0-5.0 (pass at 75%)', 'scale': _grade_scale(
        (0, 5, ''), (75, 3, ''), (76, 2.75, ''), (79, 2.5, ''), (82, 2.25, ''), (85, 2, ''), (88, 1.75, ''),
        (91, 1.5, ''), (94, 1.25, ''), (97, 1, ''))},
}
GRADE_SCALE_TEMPLATE_CHOICES = tuple((key, template['label']) for key, template in GRADE_SCALE_TEMPLATES.items())
