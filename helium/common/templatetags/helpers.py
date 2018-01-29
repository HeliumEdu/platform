from future.standard_library import install_aliases

install_aliases()

from django import template

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

register = template.Library()


@register.simple_tag
def active(request, pattern):
    try:
        if (request.path == '/' == pattern) or (pattern != '/' and request.path.startswith(pattern)):
            return 'active'
    except:
        pass
    return ''
