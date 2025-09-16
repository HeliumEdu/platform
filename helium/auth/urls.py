__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.32"

from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView

from helium.auth.views.apis.tokenresourceviews import ObtainTokenResourceView, DestroyTokenResourceView
from helium.auth.views.apis.userauthresourceviews import UserRegisterResourceView, UserVerifyResourceView, \
    UserForgotResourceView
from helium.auth.views.apis.userprofileviews import UserProfileApiDetailView
from helium.auth.views.apis.userpushtoken import UserPushTokenApiDetailView, UserPushTokenApiListView
from helium.auth.views.apis.usersettingsviews import UserSettingsApiDetailView
from helium.auth.views.apis.userviews import UserApiDetailView, UserDeleteResourceView

urlpatterns = [
    # URLs for Django's auto-generated, session-based login views for ease of API navigation
    path('login/', LoginView.as_view(redirect_authenticated_user=True,
                                     extra_context={'title': 'Login', 'site_title': settings.PROJECT_NAME,
                                                    'site_header': settings.PROJECT_NAME}), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    ##############################
    # Unauthenticated URLs
    ##############################
    path('auth/user/register/', UserRegisterResourceView.as_view({'post': 'register'}),
         name='auth_user_resource_register'),
    path('auth/user/verify/', UserVerifyResourceView.as_view({'get': 'verify_email'}),
         name='auth_user_resource_verify'),
    path('auth/user/forgot/', UserForgotResourceView.as_view({'put': 'forgot_password'}),
         name='auth_user_resource_forgot'),

    ##############################
    # Authentication URLs
    ##############################
    path('auth/token/', TokenObtainPairView.as_view(), name='auth_token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth_token_refresh'),
    path('auth/token/blacklist/', TokenBlacklistView.as_view(), name='auth_token_blacklist'),
    # Endpoints for legacy tokens, still used by the website, but will be removed once it is updated to use JWT tokens
    path('auth/legacy/token/', ObtainTokenResourceView.as_view(), name='auth_legacy_token_resource_obtain'),
    path('auth/legacy/token/revoke/', DestroyTokenResourceView.as_view({'delete': 'revoke'}),
         name='auth_legacy_token_resource_revoke'),

    ##############################
    # Authenticated URLs
    ##############################
    # User
    path('auth/user/', UserApiDetailView.as_view(), name='auth_user_detail'),
    path('auth/user/delete/', UserDeleteResourceView.as_view(), name='auth_user_resource_delete'),
    path('auth/user/profile/', UserProfileApiDetailView.as_view(),
         name='auth_user_profile_detail'),
    path('auth/user/settings/', UserSettingsApiDetailView.as_view(),
         name='auth_user_settings_detail'),
    path('auth/user/pushtoken/', UserPushTokenApiListView.as_view(),
         name='auth_user_pushtoken_list'),
    path('auth/user/pushtoken/<int:pk>/', UserPushTokenApiDetailView.as_view(),
         name='auth_user_pushtoken_detail'),
]
