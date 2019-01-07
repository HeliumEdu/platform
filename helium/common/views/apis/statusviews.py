import copy
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import psutil
from django.http import JsonResponse
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import never_cache
from health_check.contrib.psutil.backends import MemoryUsage, DiskUsage
from health_check.plugins import plugin_dir
from rest_framework import status
from rest_framework.viewsets import ViewSet

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.37"


def _run_checks(plugins):
    errors = []

    def _run(plugin):
        plugin.run_check()
        try:
            return plugin.errors
        finally:
            from django.db import connection
            connection.close()

    with ThreadPoolExecutor(max_workers=len(plugins) or 1) as executor:
        for plugin, ers in zip(plugins, executor.map(_run, plugins)):
            if plugin.critical:
                errors.extend(ers)

    return errors


def _build_components_status(plugins):
    components = {}
    system_level = sys.maxsize
    system_status = _('operational')
    for p in plugins:
        components[str(p.identifier())] = {
            "status": p.severity[1] if p.errors else _('operational'),
            "description": p.description,
            "took": round(getattr(p, 'time_taken', -1), 4)
        }
        if p.critical and p.errors and p.severity[0] < system_level:
            system_level = p.severity[0]
            system_status = components[str(p.identifier())]["status"]

    return components, system_status


class StatusResourceView(ViewSet):
    """
    status:
    Check the status of the system and its dependencies.
    """

    @never_cache
    def status(self, request, *args, **kwargs):
        plugins = sorted((
            plugin_class(**copy.deepcopy(options))
            for plugin_class, options in plugin_dir._registry
        ), key=lambda plugin: plugin.identifier())

        errors = _run_checks(plugins)

        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR if errors else status.HTTP_200_OK

        components, system_status = _build_components_status(plugins)

        return JsonResponse(
            {
                "components": components,
                "status": system_status
            },
            status=status_code
        )


class HealthResourceView(ViewSet):
    """
    health:
    Check the health of this node and its dependencies.
    """

    @never_cache
    def health(self, request, *args, **kwargs):
        plugins = sorted((
            plugin_class(**copy.deepcopy(options))
            for plugin_class, options in plugin_dir._registry
        ), key=lambda plugin: plugin.identifier())
        plugins.append(DiskUsage())
        plugins.append(MemoryUsage())

        errors = _run_checks(plugins)

        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR if errors else status.HTTP_200_OK

        components, system_status = _build_components_status(plugins)

        return JsonResponse(
            {
                "components": components,
                "uptime": round(time.time() - psutil.boot_time(), 2),
                "disk_usage": '{}%'.format(psutil.disk_usage('/').percent),
                "memory_available": '{} MB'.format(int(psutil.virtual_memory().available / 1024 / 1024)),
                "status": system_status
            },
            status=status_code
        )
