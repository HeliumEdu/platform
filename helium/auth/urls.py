from django.conf import settings
from django.conf.urls import url
from django.contrib.auth.views import LoginView, LogoutView

from helium.auth.views.apis.tokenresourceviews import ObtainTokenResourceView, DestroyTokenResourceView
from helium.auth.views.apis.userauthresourceviews import UserRegisterResourceView, UserVerifyResourceView, \
    UserForgotResourceView
from helium.auth.views.apis.userprofileviews import UserProfileApiDetailView
from helium.auth.views.apis.usersettingsviews import UserSettingsApiDetailView
from helium.auth.views.apis.userviews import UserApiDetailView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'

urlpatterns = [
    # URLs for Django's auto-generated, session-based login views for ease of API navigation
    url(r'^login/$', LoginView.as_view(redirect_authenticated_user=True,
                                       extra_context={'title': 'Login', 'site_title': settings.PROJECT_NAME,
                                                      'site_header': settings.PROJECT_NAME}), name='login'),
    url(r'^logout/$', LogoutView.as_view(), name='logout'),

    ##############################
    # Unauthenticated URLs
    ##############################
    url(r'^auth/user/register/$', UserRegisterResourceView.as_view({'post': 'register'}),
        name='auth_user_resource_register'),
    url(r'^auth/user/verify/$', UserVerifyResourceView.as_view({'get': 'verify_email'}),
        name='auth_user_resource_verify'),
    url(r'^auth/user/forgot/$', UserForgotResourceView.as_view({'put': 'forgot_password'}),
        name='auth_user_resource_forgot'),

    ##############################
    # Authentication URLs
    ##############################
    url(r'^auth/token/$', ObtainTokenResourceView.as_view(), name='auth_token_resource_obtain'),
    url(r'^auth/token/revoke/$', DestroyTokenResourceView.as_view({'delete': 'revoke'}),
        name='auth_token_resource_revoke'),

    ##############################
    # Authenticated URLs
    ##############################
    # User
    url(r'^auth/user/$', UserApiDetailView.as_view(), name='auth_user_detail'),
    url(r'^auth/user/profile/$', UserProfileApiDetailView.as_view(),
        name='auth_user_profile_detail'),
    url(r'^auth/user/settings/$', UserSettingsApiDetailView.as_view(),
        name='auth_user_settings_detail'),
]
