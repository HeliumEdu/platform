__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from helium.auth.views.apis.tokenviews import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from helium.auth.views.apis.userauthresourceviews import UserRegisterResourceView, UserVerifyResourceView, \
    UserForgotResourceView, UserResendVerificationResourceView
from helium.auth.views.apis.userdeletemanyviews import UserDeleteExampleScheduleView
from helium.auth.views.apis.userprofileviews import UserProfileApiDetailView
from helium.auth.views.apis.userpushtoken import UserPushTokenApiDetailView, UserPushTokenApiListView
from helium.auth.views.apis.usersettingsviews import UserSettingsApiDetailView
from helium.auth.views.apis.userviews import UserApiDetailView, UserDeleteResourceView, UserDeleteInactiveResourceView

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
    path('auth/user/verify/resend/', UserResendVerificationResourceView.as_view({'get': 'resend_verification'}),
         name='auth_user_resource_resend_verification'),
    path('auth/user/forgot/', UserForgotResourceView.as_view({'put': 'forgot_password'}),
         name='auth_user_resource_forgot'),

    ##############################
    # Authentication URLs
    ##############################
    path('auth/token/', TokenObtainPairView.as_view(), name='auth_token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth_token_refresh'),
    path('auth/token/blacklist/', TokenBlacklistView.as_view(), name='auth_token_blacklist'),

    ##############################
    # Authenticated URLs
    ##############################
    # User
    path('auth/user/', UserApiDetailView.as_view(), name='auth_user_detail'),
    path('auth/user/delete/', UserDeleteResourceView.as_view(), name='auth_user_resource_delete'),
    path('auth/user/delete/inactive/', UserDeleteInactiveResourceView.as_view(),
         name='auth_user_resource_delete_inactive'),
    path('auth/user/profile/', UserProfileApiDetailView.as_view(),
         name='auth_user_profile_detail'),
    path('auth/user/settings/', UserSettingsApiDetailView.as_view(),
         name='auth_user_settings_detail'),
    path('auth/user/pushtoken/', UserPushTokenApiListView.as_view(),
         name='auth_user_pushtoken_list'),
    path('auth/user/pushtoken/<int:pk>/', UserPushTokenApiDetailView.as_view(),
         name='auth_user_pushtoken_detail'),

    ##############################
    # Authenticated URLs for many-delete actions
    ##############################
    path('auth/user/delete/exampleschedule/', UserDeleteExampleScheduleView.as_view(),
         name='auth_user_resource_delete_exampleschedule'),
]
