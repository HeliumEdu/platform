__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from helium.common.timezones import TIME_ZONE_CHOICES  # noqa: F401

PYTHON_TO_HELIUM_DAY_OF_WEEK = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 0}

MONTH = 0
WEEK = 1
DAY = 2
LIST = 3
AGENDA_WEEK = 4
VIEW_CHOICES = (
    (MONTH, 'Month'),
    (WEEK, 'Week'),
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

POPUP = 0
EMAIL = 1
TEXT = 2
PUSH = 3
REMINDER_TYPE_CHOICES = (
    (POPUP, 'Popup'),
    (EMAIL, 'Email'),
    (TEXT, 'Text'),
    (PUSH, 'Push')
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
MATERIAL_STATUS_CHOICES = (
    (OWNED, 'Owned'),
    (RENTED, 'Rented'),
    (ORDERED, 'Ordered'),
    (SHIPPED, 'Shipped'),
    (NEED, 'Need'),
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

LIGHT = 0
DARK = 1
SYSTEM = 2
COLOR_SCHEME_THEME = (
    (LIGHT, 'Light'),
    (DARK, 'Dark'),
    (SYSTEM, 'System'),
)
