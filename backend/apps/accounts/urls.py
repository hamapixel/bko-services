from django.urls import path

from .views import LoginView, LogoutView, ProfileView, RegisterView, RequestPhoneCodeView, VerifyPhoneView, csrf_token

urlpatterns = [
    path("csrf/", csrf_token, name="auth-csrf"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", ProfileView.as_view(), name="auth-me"),
    path("phone/request-code/", RequestPhoneCodeView.as_view(), name="auth-phone-request-code"),
    path("phone/verify/", VerifyPhoneView.as_view(), name="auth-phone-verify"),
]
