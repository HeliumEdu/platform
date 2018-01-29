import logging

from django.contrib.auth import authenticate, login, logout, get_user_model
from django.core.urlresolvers import reverse

from helium.auth.tasks import send_verification_email, send_registration_email, send_password_reset_email
from helium.common.utils import metricutils
from helium.common.utils.viewutils import set_request_status

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def process_register(request, user):
    """
    At this point the user will be created in the database, but marked as inactive. They will not be active until
    the verification process is complete.

    :param request: the request being processed
    :param user: the user that has been created
    :return: a redirect for the next page in the registration flow
    """
    logger.info('Registered new user with username: {}'.format(user.get_username()))

    send_verification_email.delay(user.email, user.username, user.verification_code)

    set_request_status(request, 'info',
                       'You\'re almost there! The last step is to verify your email address. Click the link in the '
                       'email we just sent you and your registration will be complete!')

    return reverse('login')


def process_verification(request, username, verification_code):
    """
    If the username and verification code match values in the database, the user will be marked as active and logged in.

    :param request: the request being processed
    :param username: the username to validate against
    :param verification_code: the verification code to process
    :return: a redirect for the next page in the registration flow (logged in landing page if successful)
    """
    try:
        user = get_user_model().objects.get(username=username, verification_code=verification_code)

        if not user.is_active:
            logger.info('Verified user {}'.format(username))

            user.is_active = True
            user.save()

            if not user.email.endswith('@heliumedu.com'):
                metricutils.increment('action.user.created', request)

            send_registration_email.delay(user.email)

            # Now that the user is registered, log them it automatically and redirect them to the authenticated
            # landing page
            user.backend = 'django.contrib.auth.backends.AllowAllUsersModelBackend'
            login(request, user)

            logger.info('Completed registration and verification for user {}'.format(username))

            redirect = reverse('planner')
        elif user.email_changing:
            user.email = user.email_changing
            user.email_changing = None
            user.save()

            logger.info('Verified new email for user {}'.format(username))

            # Now that the email is verified, log the user is automatically and redirect them to the settings page
            user.backend = 'django.contrib.auth.backends.AllowAllUsersModelBackend'
            login(request, user)

            redirect = reverse('settings')
        else:
            redirect = reverse('login')
    except get_user_model().DoesNotExist:
        redirect = reverse('register')

    return redirect


def process_login(request, username, password):
    redirect = None

    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            login(request, user)

            logger.info('Logged in user {}'.format(username))

            if request.POST.get('remember-me', False):
                request.session.set_expiry(1209600)

            # If 'next' exists as a parameter in the URL, redirect to the specified page instead
            if 'next' in request.GET:
                redirect = request.GET['next']
            else:
                redirect = reverse('planner')
        else:
            logger.info('Inactive user {} attempted login'.format(username))

            set_request_status(request, 'warning',
                               'Sorry, your account is not active. Check your email for a verification email if you '
                               'recently registered, otherwise <a href="{}">contact us</a> and we\'ll help you sort '
                               'this out!'.format(reverse('contact')))
    else:
        logger.info('Non-existent user {} attempted login'.format(username))

        set_request_status(request, 'warning',
                           'Oops! We don\'t recognize that account. Check to make sure you entered your '
                           'credentials properly.')

    return redirect


def process_logout(request):
    email = request.user.email
    logout(request)
    logger.info('Logged out user {}'.format(email))


def process_forgot_password(request):
    email = request.POST['email']
    try:
        user = get_user_model().objects.get(email=email)

        # Generate a random password for the user
        password = get_user_model().objects.make_random_password()
        user.set_password(password)
        user.save()

        logger.info('Reset password for user with email {}'.format(email))

        send_password_reset_email.delay(user.email, password)

        request.session.modified = True
    except get_user_model().DoesNotExist:
        logger.info('A visitor tried to reset the password for an unknown email address of {}'.format(email))

    set_request_status(request, 'info',
                       'You\'ve been emailed a temporary password. Login to your account immediately using the '
                       'temporary password, then change your password.')

    return reverse('login')
