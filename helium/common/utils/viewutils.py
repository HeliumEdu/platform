"""
Utility functions for view data.
"""
import ast

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


def set_request_status(request, status_type, message):
    request.session['status'] = {'type': status_type, 'msg': message}


def get_request_status(request, default=None):
    status = request.session.get('status', default)

    if not status:
        status = request.COOKIES.get('status', None)
        if status:
            status = ast.literal_eval(status)

    if 'status' in request.session:
        del request.session['status']

    return status


def set_response_status(response, status):
    if status:
        response.set_cookie('status', status)


def clear_response_status(response):
    response.delete_cookie(key='status')
