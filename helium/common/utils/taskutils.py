__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
from typing import Optional

from kombu.exceptions import OperationalError

from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


def safe_apply_async(task, args=None, kwargs=None, critical=False, **options) -> Optional[object]:
    try:
        return task.apply_async(args=args, kwargs=kwargs, **options)
    except OperationalError:
        logger.warning(f"Failed to dispatch task {task.name}, broker may be unavailable",
                       exc_info=True)
        if critical:
            metricutils.increment("task.sync_fallback", extra_tags=[f"name:{task.name}"])
            logger.info(f"Executing {task.name} synchronously as fallback")
            return task.apply(args=args, kwargs=kwargs)
        return None


def safe_delay(task, *args, critical=False, **kwargs) -> Optional[object]:
    try:
        return task.delay(*args, **kwargs)
    except OperationalError:
        logger.warning(f"Failed to dispatch task {task.name}, broker may be unavailable",
                       exc_info=True)
        if critical:
            metricutils.increment("task.sync_fallback", extra_tags=[f"name:{task.name}"])
            logger.info(f"Executing {task.name} synchronously as fallback")
            return task.apply(args=args, kwargs=kwargs)
        return None
