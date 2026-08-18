__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

from django_celery_results.models import TaskResult


class TaskResultProxy(TaskResult):
    class Meta:
        proxy = True
        app_label = 'helium_common'
        verbose_name = 'Task result event'
        verbose_name_plural = 'Task results events'
