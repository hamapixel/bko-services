from django.urls import path

from .views import (
    AvatarView,
    ChangePasswordView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ProfileView,
    RegisterView,
    RequestPhoneCodeView,
    VerifyPhoneView,
    csrf_token,
)

urlpatterns = [
    path("csrf/", csrf_token, name="auth-csrf"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
    path("avatar/", AvatarView.as_view(), name="auth-avatar"),
    path(
        "password-reset/request/",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset-request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("me/", ProfileView.as_view(), name="auth-me"),
    path("phone/request-code/", RequestPhoneCodeView.as_view(), name="auth-phone-request-code"),
    path("phone/verify/", VerifyPhoneView.as_view(), name="auth-phone-verify"),
]
