"""Qarz va to'lov biznes mantiqi.

Bu modul — qoldiq, holat va to'lovlar bo'yicha **yagona haqiqat manbai**.
Serializer, view, dashboard va hisobotlar bir xil funksiyalardan foydalanadi.
Shu tufayli bir xil formula bir necha joyda takrorlanmaydi.

Asosiy tushunchalar:
- `paid_total` — faqat bekor qilinmagan to'lovlar yig'indisi;
- `remaining` — qarz summasi minus to'langan summa (hech qachon manfiy emas);
- `status` — open / partial / paid;
- `is_overdue` — qoldiq bor va muddat o'tgan;
- `display_status` — overdue bo'lsa "overdue", aks holda `status`.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone

from .choices import DebtDirection, DebtStatus, PaymentMethod
from .exceptions import (
    DebtHasPaymentsError,
    InvalidPaymentAmountError,
    InvalidPaymentMethodError,
    OverpaymentError,
    PaymentAlreadyReversedError,
    ReversalReasonRequiredError,
)
from .models import Debt, Payment

# Pul maydonlari uchun yagona Django maydon turi.
MONEY_FIELD = DecimalField(max_digits=14, decimal_places=2)
ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def money(value):
    """Qiymatni Decimal(14, 2) ko'rinishiga keltiradi.

    Bazadan kelgan summalar odatda allaqachon Decimal bo'ladi. Bu funksiya
    hisob-kitob natijalarini bir xil ko'rinishda qaytarish uchun kerak.
    """
    if value is None:
        return ZERO
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _sum_field(queryset, field):
    """Bitta maydon bo'yicha yig'indi (Decimal, 2 xona)."""
    result = queryset.aggregate(
        total=Coalesce(Sum(field), Value(ZERO), output_field=MONEY_FIELD)
    )
    return money(result["total"])


def annotate_debt_totals(queryset):
    """Qarz queryset'iga `paid_total` va `remaining` ni qo'shadi.

    `paid_total` uchun Subquery ishlatiladi. Sabab: oddiy `Sum("payments__amount")`
    JOIN hosil qiladi va bir nechta to'lov bo'lsa qarz qatori bir necha marta
    takrorlanadi. Keyin `Sum("amount")` noto'g'ri (ko'paytirilgan) natija beradi.
    Subquery esa har bir qarz uchun bitta qiymat qaytaradi.
    """
    if "paid_total" in queryset.query.annotations:
        return queryset

    paid_subquery = (
        Payment.objects.filter(
            debt=OuterRef("pk"),
            is_reversed=False,
        )
        .order_by()
        .values("debt")
        .annotate(total=Sum("amount"))
        .values("total")
    )

    paid_total = Coalesce(
        Subquery(paid_subquery, output_field=MONEY_FIELD),
        Value(ZERO),
        output_field=MONEY_FIELD,
    )

    remaining = Greatest(
        ExpressionWrapper(F("amount") - paid_total, output_field=MONEY_FIELD),
        Value(ZERO),
        output_field=MONEY_FIELD,
    )

    return queryset.annotate(paid_total=paid_total, remaining=remaining)


def get_paid_total(debt):
    """Bitta qarz bo'yicha faol to'lovlar yig'indisi."""
    if debt.pk is None:
        return ZERO

    result = Payment.objects.filter(
        debt_id=debt.pk,
        is_reversed=False,
    ).aggregate(
        total=Coalesce(Sum("amount"), Value(ZERO), output_field=MONEY_FIELD)
    )
    return money(result["total"])


def build_debt_summary(*, amount, paid_total, due_date, today=None):
    """Qarz holatini sof funksiya sifatida hisoblaydi.

    Bu funksiya bazaga murojaat qilmaydi, shuning uchun test qilish oson.
    `today` parametri testlarda sanani boshqarish uchun kerak.
    """
    today = today or timezone.localdate()
    amount = money(amount)
    paid_total = money(paid_total)
    remaining = max(amount - paid_total, ZERO)

    if remaining <= ZERO:
        status = DebtStatus.PAID.value
    elif paid_total > ZERO:
        status = DebtStatus.PARTIAL.value
    else:
        status = DebtStatus.OPEN.value

    is_overdue = bool(due_date and remaining > ZERO and due_date < today)
    display_status = DebtStatus.OVERDUE.value if is_overdue else status
    days_overdue = (today - due_date).days if is_overdue else 0

    return {
        "amount": amount,
        "paid_total": paid_total,
        "remaining": remaining,
        "status": status,
        "display_status": display_status,
        "is_overdue": is_overdue,
        "days_overdue": days_overdue,
        "due_date": due_date,
    }


def get_debt_summary(debt, *, today=None):
    """Qarz obyekti uchun to'liq hisob-kitob.

    Agar qarz `annotate_debt_totals()` bilan olingan bo'lsa, qo'shimcha
    so'rov yubormaymiz — tayyor `paid_total` dan foydalanamiz.
    """
    paid_total = debt.__dict__.get("paid_total")
    if paid_total is None:
        paid_total = get_paid_total(debt)

    return build_debt_summary(
        amount=debt.amount,
        paid_total=paid_total,
        due_date=debt.due_date,
        today=today,
    )


def _normalize_payment_amount(amount):
    """To'lov summasini tekshiradi va 2 xonaga keltiradi."""
    try:
        value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise InvalidPaymentAmountError("To'lov summasi noto'g'ri.")

    if not value.is_finite() or value <= ZERO:
        raise InvalidPaymentAmountError(
            "To'lov summasi noldan katta bo'lishi kerak."
        )

    quantized = value.quantize(CENT, rounding=ROUND_HALF_UP)
    if quantized != value:
        raise InvalidPaymentAmountError(
            "To'lov summasi 2 ta o'nlik xonadan oshmasligi kerak."
        )

    return quantized


def _actor(user):
    """AnonymousUser yoki None bo'lsa, audit maydoniga None yozamiz."""
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    return None


def _user_business_id(user):
    """Foydalanuvchining biznes ID'sini xavfsiz qaytaradi."""
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.business.id
    except (AttributeError, ObjectDoesNotExist):
        return None


def _ensure_business_access(user, business_id):
    """Foydalanuvchi boshqa biznesning qarziga to'lov qila olmasligi uchun.

    API qatlami ham business bo'yicha filtrlaydi; bu — qo'shimcha himoya.
    """
    user_business_id = _user_business_id(user)
    if user_business_id is not None and user_business_id != business_id:
        raise PermissionError("Bu biznes ma'lumotlariga ruxsat yo'q.")


def add_payment(
    debt,
    *,
    amount,
    payment_date=None,
    method=PaymentMethod.CASH,
    note="",
    user=None,
):
    """Qarzga to'lov qo'shadi.

    Jarayon atomar:
    1. qarz qatori qulflanadi (`select_for_update`);
    2. faol to'lovlar yig'indisi hisoblanadi;
    3. summa qoldiqdan oshmasligi tekshiriladi;
    4. to'lov yaratiladi.

    Tekshiruv va yozish bitta tranzaksiyada bo'lgani uchun ikki so'rov bir
    vaqtda kelganda ham ortiqcha to'lov yozilmaydi (SQLite'da yozish
    ketma-ket bo'ladi; PostgreSQL'da qator qulfi ishlaydi).
    """
    payment_amount = _normalize_payment_amount(amount)

    if method not in PaymentMethod.values:
        raise InvalidPaymentMethodError("To'lov turi noto'g'ri.")

    with transaction.atomic():
        locked_debt = Debt.objects.select_for_update().get(pk=debt.pk)
        _ensure_business_access(user, locked_debt.business_id)

        paid_total = get_paid_total(locked_debt)
        remaining = money(locked_debt.amount) - paid_total

        if remaining <= ZERO:
            raise OverpaymentError(ZERO)
        if payment_amount > remaining:
            raise OverpaymentError(remaining)

        payment = Payment.objects.create(
            debt=locked_debt,
            amount=payment_amount,
            payment_date=payment_date or timezone.localdate(),
            method=method,
            note=note or "",
            created_by=_actor(user),
        )

    return payment


def reverse_payment(payment, *, reason, user=None):
    """To'lovni bekor qiladi (hard delete emas).

    To'lov bazada qoladi, `is_reversed=True` bo'ladi va sabab saqlanadi.
    Qoldiq keyingi hisob-kitobda avtomatik oshadi.
    """
    reason = (reason or "").strip()
    if not reason:
        raise ReversalReasonRequiredError(
            "Bekor qilish sababini kiritish majburiy."
        )

    with transaction.atomic():
        # Qulf tartibi `add_payment` bilan bir xil: avval qarz, keyin to'lov.
        locked_debt = Debt.objects.select_for_update().get(pk=payment.debt_id)
        _ensure_business_access(user, locked_debt.business_id)

        locked_payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if locked_payment.is_reversed:
            raise PaymentAlreadyReversedError(
                "Bu to'lov allaqachon bekor qilingan."
            )

        locked_payment.is_reversed = True
        locked_payment.reversed_at = timezone.now()
        locked_payment.reversal_reason = reason
        locked_payment.reversed_by = _actor(user)
        locked_payment.save(
            update_fields=[
                "is_reversed",
                "reversed_at",
                "reversal_reason",
                "reversed_by",
            ]
        )

    return locked_payment


def can_delete_debt(debt):
    """Qarzni o'chirish xavfsizmi? To'lov tarixi bo'lsa — yo'q."""
    return not debt.payments.exists()


def delete_debt(debt):
    """Faqat to'lovi yo'q qarzni o'chiradi.

    To'lovi bor qarz moliyaviy tarix hisoblanadi; uni o'chirish taqiqlanadi.
    Bunday qarzni `archive_debt()` orqali arxivlash kerak.
    """
    with transaction.atomic():
        locked_debt = Debt.objects.select_for_update().get(pk=debt.pk)
        if locked_debt.payments.exists():
            raise DebtHasPaymentsError(
                "To'lovlari bor qarzni o'chirish mumkin emas. "
                "Uni arxivlang."
            )
        locked_debt.delete()


def archive_debt(debt, *, archived=True):
    """Qarzni arxivlaydi yoki arxivdan qaytaradi."""
    debt.is_archived = archived
    debt.save(update_fields=["is_archived", "updated_at"])
    return debt


def filter_debts_by_status(queryset, status, *, today=None):
    """Qarzni hisoblangan holati bo'yicha filtrlaydi.

    `open` va `partial` bazaviy holatni bildiradi; muddati o'tgan qarz ham
    ularga kirishi mumkin. Faqat muddati o'tganlarni olish uchun
    `status="overdue"` ishlatiladi.
    """
    status = (status or "").strip()
    if status not in DebtStatus.values:
        raise ValueError(f"Noma'lum qarz holati: {status}")

    today = today or timezone.localdate()
    debts = annotate_debt_totals(queryset)

    if status == DebtStatus.OPEN:
        return debts.filter(paid_total=ZERO, remaining__gt=ZERO)
    if status == DebtStatus.PARTIAL:
        return debts.filter(paid_total__gt=ZERO, remaining__gt=ZERO)
    if status == DebtStatus.PAID:
        return debts.filter(remaining__lte=ZERO)

    # OVERDUE
    return debts.filter(remaining__gt=ZERO, due_date__lt=today)


def get_contact_debt_summary(contact, *, include_archived=False):
    """Mijoz sahifasi uchun yo'nalishlar bo'yicha jamlanma.

    "Menga qarzdor" va "men qarzdorman" summasi **hech qachon birlashtirilmaydi**.

    Summalar ikki manbadan alohida olinadi: qarz summasi `Debt` dan, to'langan
    summa `Payment` dan. Sabab: `paid_total` Subquery asosida hisoblanadi va
    uni yana SQL `Sum()` bilan yig'ish SQLite'da ishonchsiz natija beradi.
    """
    debts = Debt.objects.filter(contact=contact)
    if not include_archived:
        debts = debts.filter(is_archived=False)

    result = {}
    for direction in (DebtDirection.RECEIVABLE, DebtDirection.PAYABLE):
        direction_debts = debts.filter(direction=direction)
        total_amount = _sum_field(direction_debts, "amount")
        paid_total = _sum_field(
            Payment.objects.filter(
                debt__in=direction_debts.values("pk"),
                is_reversed=False,
            ),
            "amount",
        )

        result[direction.value] = {
            "count": direction_debts.count(),
            "total_amount": total_amount,
            "paid_total": paid_total,
            "remaining": max(total_amount - paid_total, ZERO),
        }

    result["total_count"] = (
        result[DebtDirection.RECEIVABLE.value]["count"]
        + result[DebtDirection.PAYABLE.value]["count"]
    )
    return result
