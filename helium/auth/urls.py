from django.conf.urls import url

from helium.auth.views.apis.tokenviews import ObtainAuthToken, DestroyAuthToken
from helium.auth.views.apis.userauthresourceviews import UserRegisterResourceView, UserVerifyResourceView, \
    UserForgotResourceView
from helium.auth.views.apis.userprofileviews import UserProfileApiDetailView
from helium.auth.views.apis.usersettingsviews import UserSettingsApiDetailView
from helium.auth.views.apis.userviews import UserApiDetailView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'

urlpatterns = [
    ##############################
    # Unauthenticated URLs
    ##############################
    url(r'^api/auth/user/register/$', UserRegisterResourceView.as_view(), name='api_auth_user_resource_register'),
    url(r'^api/auth/user/verify/$', UserVerifyResourceView.as_view({'put': 'verify_email'}),
        name='api_auth_user_resource_verify'),
    url(r'^api/auth/user/forgot/$', UserForgotResourceView.as_view({'put': 'forgot_password'}),
        name='api_auth_user_resource_forgot'),

    ##############################
    # Authentication URLs
    ##############################
    url(r'^api/auth/token/$', ObtainAuthToken.as_view(), name='api_auth_token'),
    url(r'^api/auth/token/revoke/$', DestroyAuthToken.as_view({'delete': 'revoke'}), name='api_auth_token_revoke'),

    ##############################
    # Authenticated URLs
    ##############################
    # User
    url(r'^api/auth/user/$', UserApiDetailView.as_view(), name='api_auth_user_detail'),
    url(r'^api/auth/user/profile/$', UserProfileApiDetailView.as_view(),
        name='api_auth_user_profile_detail'),
    url(r'^api/auth/user/settings/$', UserSettingsApiDetailView.as_view(),
        name='api_auth_user_settings_detail'),
]
