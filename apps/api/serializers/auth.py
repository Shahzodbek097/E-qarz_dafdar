"""Autentifikatsiya va profil serializer'lari."""

from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.services import normalize_phone, register_user
from apps.businesses.choices import Industry
from apps.businesses.models import Business


class BusinessSerializer(serializers.ModelSerializer):
    industry_display = serializers.CharField(
        source="get_industry_display", read_only=True
    )

    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "industry",
            "industry_display",
            "phone",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_phone(self, value):
        try:
            return normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)


class UserSerializer(serializers.ModelSerializer):
    """Profilni o'qish va tahrirlash uchun serializer.

    `phone` maydoni qo'lda e'lon qilingan: shunda DRF'ning standart
    UniqueValidator'i xom formatni tekshirib qolmaydi. Normalizatsiya va
    dublikat tekshiruvi `validate_phone` ichida bajariladi.
    """

    full_name = serializers.CharField(read_only=True)
    phone = serializers.CharField(max_length=20, required=False)
    email = serializers.EmailField(required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "email",
            "date_joined",
        ]
        read_only_fields = ["id", "username", "date_joined"]

    def validate_phone(self, value):
        try:
            normalized = normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)

        queryset = User.objects.filter(phone=normalized)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "Bu telefon raqami allaqachon ro'yxatdan o'tgan."
            )
        return normalized

    def validate_email(self, value):
        email = (value or "").strip().lower()
        if not email:
            raise serializers.ValidationError("Elektron pochta majburiy.")

        queryset = User.objects.filter(email__iexact=email)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "Bu email allaqachon ro'yxatdan o'tgan."
            )
        return email


class RegisterSerializer(serializers.Serializer):
    """Ro'yxatdan o'tish ma'lumotlari.

    Yozuvlarni yaratish `apps.accounts.services.register_user()` orqali
    bajariladi: u User va Business'ni bitta atomar tranzaksiyada yaratadi.
    """

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    business_name = serializers.CharField(max_length=150)
    industry = serializers.ChoiceField(
        choices=Industry.choices,
        required=False,
        default=Industry.OTHER,
    )

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": ["Parollar mos kelmadi."]}
            )
        return attrs

    def create(self, validated_data):
        try:
            return register_user(**validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                getattr(
                    exc,
                    "message_dict",
                    {"non_field_errors": exc.messages},
                )
            )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["username"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError(
                {"non_field_errors": ["Login yoki parol noto'g'ri."]}
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {"non_field_errors": ["Foydalanuvchi faol emas."]}
            )
        attrs["user"] = user
        return attrs
