"""Ro'yxatdan o'tish biznes mantiqi.

Register jarayonida ikkita yozuv yaratiladi:
1. `User` — shaxsiy ma'lumotlar va parol;
2. `Business` — avtomatik yaratiladigan biznes profili.

Ikkalasi bitta `transaction.atomic()` ichida bo'ladi: agar biznes yaratishda
xato bo'lsa, foydalanuvchi ham bazaga yozilmaydi.
"""

import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from apps.businesses.choices import Industry
from apps.businesses.models import Business

from .models import User


def normalize_phone(value):
    """Telefon raqamini `+998XXXXXXXXX` ko'rinishiga keltiradi.

    Qabul qilinadigan misollar:
    - `+998 90 123 45 67`
    - `998901234567`
    - `90 123 45 67`

    Boshqa formatlar `ValidationError` bilan rad etiladi.
    """
    digits = re.sub(r"\D", "", str(value or ""))

    if digits.startswith("998") and len(digits) == 12:
        return f"+{digits}"
    if len(digits) == 9:
        return f"+998{digits}"

    raise ValidationError(
        "Telefon raqami +998XXXXXXXXX ko'rinishida bo'lishi kerak."
    )


@transaction.atomic
def register_user(
    *,
    username,
    password,
    first_name,
    last_name,
    phone,
    email,
    business_name,
    industry,
):
    """Yangi foydalanuvchi va uning biznesini atomar yaratadi.

    Xatoliklar `ValidationError` ko'rinishida maydonlar bo'yicha qaytariladi,
    masalan: `{"username": ["Bu login allaqachon band."]}`.
    API qatlami bu xatolarni foydalanuvchiga tushunarli JSON'ga aylantiradi.
    """
    username = (username or "").strip()
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()
    email = (email or "").strip().lower()
    business_name = (business_name or "").strip()
    industry = (industry or "").strip() or Industry.OTHER

    errors = {}

    if not username:
        errors["username"] = ["Login majburiy."]
    if not first_name:
        errors["first_name"] = ["Ism majburiy."]
    if not last_name:
        errors["last_name"] = ["Familiya majburiy."]
    if not email:
        errors["email"] = ["Elektron pochta majburiy."]
    if not business_name:
        errors["business_name"] = ["Biznes nomi majburiy."]
    if not password:
        errors["password"] = ["Parol majburiy."]

    if email:
        try:
            validate_email(email)
        except ValidationError as exc:
            errors["email"] = exc.messages

    if industry and industry not in Industry.values:
        errors["industry"] = ["Faoliyat sohasi noto'g'ri."]

    normalized_phone = None
    if phone:
        try:
            normalized_phone = normalize_phone(phone)
        except ValidationError as exc:
            errors["phone"] = exc.messages
    else:
        errors["phone"] = ["Telefon raqami majburiy."]

    if errors:
        raise ValidationError(errors)

    # Dublikatlarni oldindan tekshiramiz — foydalanuvchiga tushunarli xabar
    # berish uchun. Bazadagi constraintlar oxirgi himoya bo'lib qoladi.
    if User.objects.filter(username__iexact=username).exists():
        errors["username"] = ["Bu login allaqachon band."]
    if User.objects.filter(email__iexact=email).exists():
        errors["email"] = ["Bu email allaqachon ro'yxatdan o'tgan."]
    if User.objects.filter(phone=normalized_phone).exists():
        errors["phone"] = ["Bu telefon raqami allaqachon ro'yxatdan o'tgan."]

    if errors:
        raise ValidationError(errors)

    candidate = User(
        username=username,
        first_name=first_name,
        last_name=last_name,
        phone=normalized_phone,
        email=email,
    )

    try:
        validate_password(password, user=candidate)
    except ValidationError as exc:
        raise ValidationError({"password": exc.messages})

    candidate.set_password(password)
    candidate.save()

    # Agar bu qator xato bersa, `transaction.atomic()` tufayli User ham
    # bazadan o'chiriladi.
    Business.objects.create(
        owner=candidate,
        name=business_name,
        industry=industry,
        phone=normalized_phone,
    )

    return candidate
