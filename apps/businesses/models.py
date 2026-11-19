"""Biznes profili.

Har bir foydalanuvchining bitta biznesi bo'ladi. Bu bog'lanish `OneToOneField`
orqali ta'minlanadi: bitta User — bitta Business.
"""

from django.conf import settings
from django.db import models

from .choices import Industry


class Business(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business",
        verbose_name="egasi",
    )
    name = models.CharField("nomi", max_length=150)
    industry = models.CharField(
        "faoliyat sohasi",
        max_length=30,
        choices=Industry.choices,
        default=Industry.OTHER,
    )
    phone = models.CharField("telefon raqami", max_length=20)

    created_at = models.DateTimeField("yaratilgan vaqt", auto_now_add=True)
    updated_at = models.DateTimeField("o'zgartirilgan vaqt", auto_now=True)

    class Meta:
        verbose_name = "biznes"
        verbose_name_plural = "bizneslar"
        ordering = ["name"]

    def __str__(self):
        return self.name
