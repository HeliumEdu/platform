__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.urls import path

from helium.auth.views.apis.apitokenviews import ApiTokenView
from helium.auth.views.apis.oauthviews import OAuthLoginView
from helium.auth.views.apis.tokenviews import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from helium.auth.views.apis.userauthresourceviews import UserRegisterResourceView, UserVerifyResourceView, \
    UserForgotResourceView, UserForgotConfirmResourceView, UserResendVerificationResourceView
from helium.auth.views.apis.userdeleteexamplescheduleviews import UserDeleteExampleScheduleView
from helium.auth.views.apis.userpushtoken import UserPushTokenApiDetailView, UserPushTokenApiListView
from helium.auth.views.apis.userreviewpromptviews import UserReviewPromptAckView
from helium.auth.views.apis.usersettingsviews import UserSettingsApiDetailView
from helium.auth.views.apis.userviews import UserApiDetailView, UserDeleteResourceView, UserDeleteInactiveResourceView

urlpatterns = [
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
    path('auth/user/forgot/confirm/', UserForgotConfirmResourceView.as_view({'put': 'confirm_password_reset'}),
         name='auth_user_resource_forgot_confirm'),

    ##############################
    # Authentication URLs
    ##############################
    path('auth/token/', TokenObtainPairView.as_view(), name='auth_token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth_token_refresh'),
    path('auth/token/blacklist/', TokenBlacklistView.as_view(), name='auth_token_blacklist'),
    path('auth/token/oauth/', OAuthLoginView.as_view({'post': 'oauth_login'}),
         name='auth_token_oauth'),

    ##############################
    # Authenticated URLs
    ##############################
    path('auth/api-token/', ApiTokenView.as_view(), name='auth_api_token'),

    # User
    path('auth/user/', UserApiDetailView.as_view(), name='auth_user_detail'),
    path('auth/user/delete/', UserDeleteResourceView.as_view(), name='auth_user_resource_delete'),
    path('auth/user/delete/inactive/', UserDeleteInactiveResourceView.as_view(),
         name='auth_user_resource_delete_inactive'),
    path('auth/user/settings/', UserSettingsApiDetailView.as_view(),
         name='auth_user_settings_detail'),
    path('auth/user/settings/review-prompt-ack/', UserReviewPromptAckView.as_view(),
         name='auth_user_settings_review_prompt_ack'),
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
