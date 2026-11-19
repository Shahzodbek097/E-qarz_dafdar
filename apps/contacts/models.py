"""Mijozlar va hamkorlar.

Har bir Contact bitta Business'ga tegishli. Boshqa biznesning mijozlarini
ko'rishning oldini olish API qatlamida (business bo'yicha filtr) amalga
oshiriladi.
"""

from django.db import models

from apps.businesses.models import Business

from .choices import ContactType


class Contact(models.Model):
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="contacts",
        verbose_name="biznes",
    )
    name = models.CharField("ism yoki tashkilot nomi", max_length=150)
    phone = models.CharField("telefon raqami", max_length=30, blank=True)
    address = models.CharField("manzil", max_length=255, blank=True)
    type = models.CharField(
        "shaxs turi",
        max_length=20,
        choices=ContactType.choices,
        default=ContactType.CUSTOMER,
    )
    note = models.TextField("qo'shimcha izoh", blank=True)

    created_at = models.DateTimeField("yaratilgan vaqt", auto_now_add=True)
    updated_at = models.DateTimeField("o'zgartirilgan vaqt", auto_now=True)

    class Meta:
        verbose_name = "mijoz"
        verbose_name_plural = "mijozlar"
        ordering = ["name"]
        indexes = [
            # Qidiruv va ro'yxat uchun eng ko'p ishlatiladigan indekslar.
            models.Index(fields=["business", "name"], name="contact_biz_name_idx"),
            models.Index(fields=["business", "phone"], name="contact_biz_phone_idx"),
        ]

    def __str__(self):
        return self.name
