__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from dataclasses import dataclass
from typing import Any, List, Optional

from celery.schedules import crontab


@dataclass(frozen=True)
class PeriodicTaskSpec:
    task: Any
    schedule: Any
    priority: Optional[int] = None
    description: str = ""
    manually_triggerable: bool = True


PERIODIC_TASKS: List[PeriodicTaskSpec] = []


def register_periodic(task,
                      schedule,
                      priority: Optional[int] = None,
                      description: str = "",
                      manually_triggerable: bool = True) -> None:
    PERIODIC_TASKS.append(PeriodicTaskSpec(task=task,
                                           schedule=schedule,
                                           priority=priority,
                                           description=description,
                                           manually_triggerable=manually_triggerable))


def format_schedule(schedule) -> str:
    if isinstance(schedule, crontab):
        return (f"cron: m={schedule._orig_minute} h={schedule._orig_hour} "
                f"dom={schedule._orig_day_of_month} mon={schedule._orig_month_of_year} "
                f"dow={schedule._orig_day_of_week}")

    if isinstance(schedule, (int, float)):
        seconds = int(schedule)
        if seconds % 3600 == 0 and seconds >= 3600:
            return f"every {seconds // 3600}h"
        if seconds % 60 == 0 and seconds >= 60:
            return f"every {seconds // 60}m"
        return f"every {seconds}s"

    return repr(schedule)
