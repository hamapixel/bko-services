from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle
from rest_framework.views import APIView

from .otp_delivery import DeliveryUnavailable
from .otp_service import request_verification_code, verify_phone_code
from .serializers import LoginSerializer, ProfileSerializer, PublicUserSerializer, RegisterSerializer, VerifyPhoneSerializer


class SmsUnavailable(APIException):
    status_code = 503
    default_detail = "La vérification par SMS n'est pas disponible dans cet environnement."


class OtpIpThrottle(SimpleRateThrottle):
    scope = "otp_ip"

    def get_cache_key(self, request, view):
        # Use the direct peer address, not a user-supplied forwarded header.
        return self.cache_format % {"scope": self.scope, "ident": request.META.get("REMOTE_ADDR", "unknown")}


@require_GET
@never_cache
@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_register"

    def post(self, request):
        if not isinstance(request.data, dict) or set(request.data) - set(RegisterSerializer().fields):
            raise ValidationError({"detail": "Champ non autorisé."})
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(PublicUserSerializer(user).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request, **serializer.validated_data)
        if user is None:
            return Response({"detail": "Identifiants incorrects."}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response(PublicUserSerializer(user).data)


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_protect, name="dispatch")
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PublicUserSerializer(request.user).data)

    def patch(self, request):
        if not isinstance(request.data, dict) or set(request.data) - set(ProfileSerializer().fields):
            raise ValidationError({"detail": "Champ non autorisé."})
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PublicUserSerializer(request.user).data)


@method_decorator(csrf_protect, name="dispatch")
class RequestPhoneCodeView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle, OtpIpThrottle]
    throttle_scope = "otp_request"

    def post(self, request):
        try:
            request_verification_code(request.user, request.get_host(), request.META.get("REMOTE_ADDR", ""))
        except DeliveryUnavailable as exc:
            raise SmsUnavailable() from exc
        return Response({"detail": "Code envoyé si le transport SMS est disponible."})


@method_decorator(csrf_protect, name="dispatch")
class VerifyPhoneView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle, OtpIpThrottle]
    throttle_scope = "otp_verify"

    def post(self, request):
        serializer = VerifyPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not verify_phone_code(request.user, serializer.validated_data["code"]):
            raise ValidationError({"code": "Code incorrect."})
        request.user.refresh_from_db(fields=["phone_verified_at"])
        return Response({"phone_verified_at": request.user.phone_verified_at})
