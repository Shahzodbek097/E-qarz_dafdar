"""Qarz va to'lov modellari.

Muhim qoida: qarzning qoldig'i, to'langan summasi va holati bu yerda
saqlanmaydi. Ular `apps.debts.services` modulida to'lovlar tarixidan
hisoblanadi. Shu tufayli baza har doim haqiqiy to'lovlar bilan mos bo'ladi.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.businesses.models import Business
from apps.contacts.models import Contact

from .choices import DebtDirection, PaymentMethod

# Pul maydonlari uchun minimal qiymat: 0.01 (nol va manfiy taqiqlanadi).
MIN_MONEY = Decimal("0.01")


class Debt(models.Model):
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="debts",
        verbose_name="biznes",
    )
    contact = models.ForeignKey(
        Contact,
        # PROTECT: qarzi bor mijozni tasodifan o'chirib bo'lmaydi.
        on_delete=models.PROTECT,
        related_name="debts",
        verbose_name="mijoz",
    )
    direction = models.CharField(
        "qarz yo'nalishi",
        max_length=10,
        choices=DebtDirection.choices,
    )
    amount = models.DecimalField(
        "summa",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(MIN_MONEY)],
    )
    issue_date = models.DateField("qarz sanasi", default=timezone.localdate)
    due_date = models.DateField(
        "qaytarish muddati",
        null=True,
        blank=True,
    )
    reason = models.CharField("sabab / izoh", max_length=255, blank=True)
    note = models.TextField("qo'shimcha ma'lumot", blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_debts",
        verbose_name="kim yaratgan",
    )
    is_archived = models.BooleanField("arxivlangan", default=False)

    created_at = models.DateTimeField("yaratilgan vaqt", auto_now_add=True)
    updated_at = models.DateTimeField("o'zgartirilgan vaqt", auto_now=True)

    class Meta:
        verbose_name = "qarz"
        verbose_name_plural = "qarzlar"
        ordering = ["-created_at", "-id"]
        constraints = [
            # Bazaning o'zi ham nol/manfiy summani qabul qilmasligi kerak.
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="debt_amount_positive",
            ),
            # Qaytarish muddati qarz sanasidan oldin bo'lishi mumkin emas.
            models.CheckConstraint(
                condition=Q(due_date__isnull=True)
                | Q(due_date__gte=F("issue_date")),
                name="debt_due_after_issue",
            ),
        ]
        indexes = [
            models.Index(
                fields=["business", "direction"],
                name="debt_biz_direction_idx",
            ),
            models.Index(
                fields=["business", "issue_date"],
                name="debt_biz_issue_idx",
            ),
            models.Index(
                fields=["business", "due_date"],
                name="debt_biz_due_idx",
            ),
            models.Index(
                fields=["business", "contact"],
                name="debt_biz_contact_idx",
            ),
            models.Index(
                fields=["business", "is_archived"],
                name="debt_biz_archived_idx",
            ),
        ]

    def __str__(self):
        return f"{self.contact} — {self.amount}"


class Payment(models.Model):
    """Qarz bo'yicha to'lov.

    To'lovlar hech qachon hard delete qilinmaydi. Xato to'lovni bekor qilish
    uchun `is_reversed=True` qilinadi va sabab saqlanadi. Bu moliyaviy
    tarixning butunligini ta'minlaydi.
    """

    debt = models.ForeignKey(
        Debt,
        # PROTECT: to'lovi bor qarzni tasodifan o'chirib bo'lmaydi.
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="qarz",
    )
    amount = models.DecimalField(
        "summa",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(MIN_MONEY)],
    )
    payment_date = models.DateField("to'lov sanasi", default=timezone.localdate)
    method = models.CharField(
        "to'lov turi",
        max_length=10,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    note = models.TextField("izoh", blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_payments",
        verbose_name="kim kiritgan",
    )
    created_at = models.DateTimeField("yaratilgan vaqt", auto_now_add=True)

    # --- Bekor qilish (reversal) maydonlari ---
    is_reversed = models.BooleanField("bekor qilingan", default=False)
    reversed_at = models.DateTimeField(
        "bekor qilingan vaqt",
        null=True,
        blank=True,
    )
    reversal_reason = models.TextField("bekor qilish sababi", blank=True)
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversed_payments",
        verbose_name="kim bekor qilgan",
    )

    class Meta:
        verbose_name = "to'lov"
        verbose_name_plural = "to'lovlar"
        ordering = ["-payment_date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="payment_amount_positive",
            ),
            # Agar to'lov bekor qilingan bo'lsa, bekor qilingan vaqt ham
            # albatta bo'lishi kerak.
            models.CheckConstraint(
                condition=Q(is_reversed=False) | Q(reversed_at__isnull=False),
                name="payment_reversal_consistent",
            ),
        ]
        indexes = [
            models.Index(
                fields=["debt", "payment_date"],
                name="payment_debt_date_idx",
            ),
            models.Index(
                fields=["debt", "is_reversed"],
                name="payment_debt_rev_idx",
            ),
        ]

    def __str__(self):
        return f"{self.debt_id}: {self.amount}"
