import logging

from django.conf import settings
from django.db import OperationalError, connection
from django_celery_results.backends.database import DatabaseBackend

logger = logging.getLogger(__name__)


def _is_lost_connection(exc: Exception) -> bool:
    return (isinstance(exc, OperationalError)
            and bool(exc.args)
            and exc.args[0] in settings.DB_LOST_CONNECTION_ERROR_CODES)


class ResilientDatabaseBackend(DatabaseBackend):
    """
    Django DB result backend that survives MySQL dropping its connection.

    The worker's main process writes results (e.g. marking a task revoked) outside any request or
    task, so Django never recycles its connection. When MySQL drops it (a restart, or `wait_timeout`
    on an idle worker), the upstream backend only retries `InterfaceError`, so the MySQL
    `OperationalError` is fatal and takes down the worker. Here lost-connection errors are also
    retryable, and the connection is closed before each retry so the next attempt reconnects.

    Retries only happen when `result_backend_always_retry` is enabled; Celery handles the backoff.
    """

    def exception_safe_to_retry(self, exc: Exception) -> bool:
        return super().exception_safe_to_retry(exc) or _is_lost_connection(exc)

    def on_backend_retryable_error(self, exc: Exception) -> None:
        logger.warning(f"Result backend lost its database connection, reconnecting before retry: {exc}")
        connection.close()
