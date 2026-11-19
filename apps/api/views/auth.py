"""Autentifikatsiya view'lari.

Session autentifikatsiyasi ishlatiladi:
- `csrf` — frontend token oladi;
- `register` — User + Business atomar yaratiladi, avtomatik login yo'q;
- `login` / `logout` — Django session;
- `me` — joriy foydalanuvchi profili;
- `business` — joriy biznes profili.

`register` va `login` uchun CSRF `csrf_protect` bilan majburiy qilinadi:
DRF `APIView` odatda CSRF'dan ozod, lekin login CSRF hujumidan himoya
muhim.
"""

from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.mixins import BusinessScopedMixin
from apps.api.serializers import (
    BusinessSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)


def auth_payload(user):
    """Login/me javobi uchun umumiy tuzilma."""
    business = getattr(user, "business", None)
    return {
        "user": UserSerializer(user).data,
        "business": (
            BusinessSerializer(business).data if business is not None else None
        ),
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(auth_payload(user), status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        auth_login(request._request, user)
        return Response(auth_payload(user))


class LogoutView(APIView):
    def post(self, request):
        auth_logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(auth_payload(request.user))

    def patch(self, request):
        serializer = UserSerializer(
            instance=request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(auth_payload(request.user))


class BusinessView(BusinessScopedMixin, APIView):
    def get(self, request):
        return Response(BusinessSerializer(self.get_business()).data)

    def patch(self, request):
        business = self.get_business()
        serializer = BusinessSerializer(
            instance=business,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
