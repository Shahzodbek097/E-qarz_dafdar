"""Foydalanuvchi modeli.

Django'ning tayyor `AbstractUser` modelidan meros olamiz: unda username,
password, is_staff, date_joined kabi standart maydonlar bor. Biz faqat
o'zimizga kerakli qo'shimcha maydonlarni qo'shamiz.
"""

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower

# Telefon raqamini yagona formatga majburlash uchun validator.
# +998 dan keyin 9 ta raqam bo'lishi kerak.
phone_validator = RegexValidator(
    regex=r"^\+998\d{9}$",
    message="Telefon raqami +998XXXXXXXXX ko'rinishida bo'lishi kerak.",
)


class User(AbstractUser):
    """Tizim foydalanuvchisi (biznes egasi).

    `username` — tizimga kirish logini.
    `phone` — unikal telefon raqami.
    `email` — registrda case-insensitive unikal bo'ladi (pastdagi constraint).
    """

    # AbstractUser'dagi maydonlarni majburiy qilib qayta e'lon qilamiz.
    first_name = models.CharField("ism", max_length=150)
    last_name = models.CharField("familiya", max_length=150)
    email = models.EmailField("elektron pochta")

    phone = models.CharField(
        "telefon raqami",
        max_length=20,
        unique=True,
        validators=[phone_validator],
    )

    # `createsuperuser` buyrug'i qaysi maydonlarni so'rashini belgilaydi.
    REQUIRED_FIELDS = ["email", "first_name", "last_name", "phone"]

    class Meta:
        verbose_name = "foydalanuvchi"
        verbose_name_plural = "foydalanuvchilar"
        constraints = [
            # Email har xil registrda yozilsa ham takrorlanmasligi kerak:
            # "Ali@mail.com" va "ali@mail.com" bir xil hisoblanadi.
            models.UniqueConstraint(
                Lower("email"),
                name="uniq_user_email_ci",
            ),
        ]

    def __str__(self):
        return self.full_name or self.username

    @property
    def full_name(self):
        """Ism va familiyani bitta qatorga birlashtiradi."""
        return f"{self.first_name} {self.last_name}".strip()
