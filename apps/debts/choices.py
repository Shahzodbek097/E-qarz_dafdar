"""Qarz yo'nalishi va to'lov turlari."""

from django.db import models


class DebtDirection(models.TextChoices):
    # Mijoz yoki boshqa shaxs biznes egasiga qarzdor.
    RECEIVABLE = "receivable", "Menga qarzdor"
    # Biznes egasi boshqa shaxs yoki tashkilot oldida qarzdor.
    PAYABLE = "payable", "Men qarzdorman"


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Naqd"
    BANK = "bank", "Bank o'tkazmasi"
    OTHER = "other", "Boshqa"


class DebtStatus(models.TextChoices):
    """Qarz holati.

    `open`, `partial`, `paid` — bazaviy holat.
    `overdue` — faqat ko'rsatish (display) uchun hisoblanadigan holat:
    qoldiq mavjud va qaytarish muddati o'tgan.
    """

    OPEN = "open", "Ochiq"
    PARTIAL = "partial", "Qisman to'langan"
    PAID = "paid", "To'liq to'langan"
    OVERDUE = "overdue", "Muddati o'tgan"
