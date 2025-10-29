__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.15.15"

from django.conf import settings
from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django_celery_results.models import TaskResult, GroupResult


class PlatformAdminSite(AdminSite):
    """
    Creates a base AdminSite. Models and URLs should be attached to an instance of this class.
    """
    site_header = settings.PROJECT_NAME + ' Administration'
    site_title = site_header
    index_title = settings.PROJECT_NAME


class BaseModelAdmin(ModelAdmin):
    """
    All Models that inherit from BaseModel should also inherit from this BaseModelAdmin, which makes sure the common
    attributes are properly rendered in the admin area.
    """
    list_display = ('created_at', 'updated_at',)
    ordering = ('-updated_at',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('created_at', 'updated_at',)

        return self.readonly_fields


# Instantiate the Admin site
admin_site = PlatformAdminSite()


class TaskResultAdmin(ModelAdmin):
    list_display = ('task_id', 'task_name', 'date_done', 'status', 'worker')
    list_filter = ('status', 'date_done')
    search_fields = ('task_id', 'task_name')
    ordering = ('-date_done',)


admin_site.register(TaskResult, TaskResultAdmin)
