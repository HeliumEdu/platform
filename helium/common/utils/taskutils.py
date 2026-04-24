__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def safe_apply_async(task, args=None, kwargs=None, **options) -> Optional[object]:
    try:
        return task.apply_async(args=args, kwargs=kwargs, **options)
    except Exception:
        logger.warning(f"Failed to dispatch task {task.name}, broker may be unavailable",
                       exc_info=True)
        return None


def safe_delay(task, *args, **kwargs) -> Optional[object]:
    try:
        return task.delay(*args, **kwargs)
    except Exception:
        logger.warning(f"Failed to dispatch task {task.name}, broker may be unavailable",
                       exc_info=True)
        return None
