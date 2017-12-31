from future.standard_library import install_aliases

install_aliases()

from urllib.parse import urlencode

from django import template

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
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


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    query = context['request'].GET.dict()
    query.update(kwargs)
    return urlencode(query)


@register.filter
def multiply(value, arg):
    return value * arg
