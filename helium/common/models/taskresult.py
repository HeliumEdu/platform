__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django_celery_results.models import TaskResult


class TaskResultProxy(TaskResult):
    class Meta:
        proxy = True
        app_label = 'common'
        verbose_name = 'Task result'
        verbose_name_plural = 'Task results'
