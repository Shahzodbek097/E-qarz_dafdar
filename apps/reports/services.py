"""Dashboard va hisobot hisob-kitoblari.

Barcha summalar shu yerda, backendda hisoblanadi. Frontend faqat tayyor
natijalarni ko'rsatadi.

Muhim: "Menga qarzdor" (receivable) va "Men qarzdorman" (payable) summasi
hech qachon bitta raqamga qo'shilmaydi.

Hisoblash usuli:
- qarz summalari `Debt` jadvalidan olinadi;
- to'langan summalar `Payment` jadvalidan alohida olinadi;
- qoldiq = summa - to'langan (manfiy bo'lmaydi).

Nega `Sum("remaining")` ishlatilmaydi? `remaining` Subquery asosida
hisoblanadi. Uni yana SQL agregatsiyasida yig'ish SQLite'da ishonchsiz
natija beradi. Shuning uchun jamlanmalar uchun summa va to'lov alohida
so'raladi, seriyalar esa Python'da guruhlanadi.
"""

from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.debts.choices import DebtDirection, DebtStatus, PaymentMethod
from apps.debts.models import Debt, Payment
from apps.debts.services import (
    MONEY_FIELD,
    ZERO,
    annotate_debt_totals,
    money,
)


def _validate_date_range(date_from, date_to):
    if date_from and date_to and date_from > date_to:
        raise ValidationError(
            {
                "date_to": [
                    "Sana oralig'i noto'g'ri: boshlanish sanasi "
                    "tugash sanasidan katta bo'lishi mumkin emas."
                ]
            }
        )


def _validate_group_by(group_by):
    if group_by not in {"day", "month"}:
        raise ValidationError(
            {
                "group_by": [
                    "Guruhlash faqat 'day' yoki 'month' bo'lishi mumkin."
                ]
            }
        )


def _validate_direction(direction):
    if direction and direction not in DebtDirection.values:
        raise ValidationError(
            {"direction": ["Qarz yo'nalishi noto'g'ri."]}
        )


def _validate_method(method):
    if method and method not in PaymentMethod.values:
        raise ValidationError({"method": ["To'lov turi noto'g'ri."]})


def _sum(queryset, field):
    """Bitta maydon bo'yicha yig'indi (Decimal, 2 xona)."""
    result = queryset.aggregate(
        total=Coalesce(Sum(field), Value(ZERO), output_field=MONEY_FIELD)
    )
    return money(result["total"])


def _payment_sum(queryset):
    """To'lovlar bo'yicha yig'indi."""
    return _sum(queryset, "amount")


def _base_debts(business, *, include_archived=False):
    """Biznesning qarzlari + hisoblangan `paid_total` / `remaining`."""
    debts = Debt.objects.filter(business=business)
    if not include_archived:
        debts = debts.filter(is_archived=False)
    return annotate_debt_totals(debts)


def _period(value, group_by):
    """Kun yoki oy boshlanish sanasini qaytaradi."""
    return value if group_by == "day" else value.replace(day=1)


def get_dashboard_summary(business, *, today=None):
    """Dashboard uchun barcha asosiy ko'rsatkichlar.

    Qaytaradi:
    - totals: receivable, payable, overdue_*, paid_*, active_debts_count;
    - recent_debts: oxirgi 5 ta qarz (arxivlanganlar emas);
    - recent_payments: oxirgi 5 ta faol to'lov;
    - top_debtors: qoldig'i eng katta 5 ta "menga qarzdor" mijoz.
    """
    today = today or timezone.localdate()
    debts = _base_debts(business)

    receivable_amount = _sum(
        debts.filter(direction=DebtDirection.RECEIVABLE), "amount"
    )
    payable_amount = _sum(
        debts.filter(direction=DebtDirection.PAYABLE), "amount"
    )

    # To'lovlar faqat shu biznesning arxivlanmagan qarzlariga tegishli.
    paid_receivable = _payment_sum(
        Payment.objects.filter(
            debt__business=business,
            debt__direction=DebtDirection.RECEIVABLE,
            debt__is_archived=False,
            is_reversed=False,
        )
    )
    paid_payable = _payment_sum(
        Payment.objects.filter(
            debt__business=business,
            debt__direction=DebtDirection.PAYABLE,
            debt__is_archived=False,
            is_reversed=False,
        )
    )

    receivable = max(receivable_amount - paid_receivable, ZERO)
    payable = max(payable_amount - paid_payable, ZERO)

    overdue_debts = debts.filter(
        remaining__gt=ZERO,
        due_date__lt=today,
    )
    overdue_receivable_amount = _sum(
        overdue_debts.filter(direction=DebtDirection.RECEIVABLE), "amount"
    )
    overdue_payable_amount = _sum(
        overdue_debts.filter(direction=DebtDirection.PAYABLE), "amount"
    )

    overdue_receivable_paid = _payment_sum(
        Payment.objects.filter(
            debt__in=overdue_debts.filter(
                direction=DebtDirection.RECEIVABLE
            ).values("pk"),
            is_reversed=False,
        )
    )
    overdue_payable_paid = _payment_sum(
        Payment.objects.filter(
            debt__in=overdue_debts.filter(
                direction=DebtDirection.PAYABLE
            ).values("pk"),
            is_reversed=False,
        )
    )

    overdue_receivable = max(
        overdue_receivable_amount - overdue_receivable_paid, ZERO
    )
    overdue_payable = max(
        overdue_payable_amount - overdue_payable_paid, ZERO
    )

    active_debts_count = debts.filter(remaining__gt=ZERO).count()

    recent_debts = list(
        debts.select_related("contact").order_by("-created_at", "-id")[:5]
    )

    recent_payments = list(
        Payment.objects.filter(
            debt__business=business,
            is_reversed=False,
        )
        .select_related("debt", "debt__contact")
        .order_by("-payment_date", "-id")[:5]
    )

    # Top qarzdorlarni kontakt bo'yicha guruhlaymiz. Har bir qarz uchun
    # qoldiq = summa - faol to'lovlar.
    top_rows = debts.filter(
        direction=DebtDirection.RECEIVABLE,
        remaining__gt=ZERO,
    ).values(
        "contact_id",
        "contact__name",
        "contact__phone",
        "amount",
        "paid_total",
    )

    grouped = {}
    for row in top_rows:
        remaining = money(row["amount"]) - money(row["paid_total"])
        if remaining <= ZERO:
            continue
        contact_id = row["contact_id"]
        if contact_id not in grouped:
            grouped[contact_id] = {
                "contact_id": contact_id,
                "name": row["contact__name"],
                "phone": row["contact__phone"],
                "remaining": ZERO,
            }
        grouped[contact_id]["remaining"] += remaining

    top_debtors = sorted(
        grouped.values(),
        key=lambda item: (-item["remaining"], item["name"]),
    )[:5]

    return {
        "totals": {
            "receivable": receivable,
            "payable": payable,
            "overdue_receivable": overdue_receivable,
            "overdue_payable": overdue_payable,
            "paid_receivable": paid_receivable,
            "paid_payable": paid_payable,
            "paid_total": paid_receivable + paid_payable,
            "active_debts_count": active_debts_count,
            "overdue_count": overdue_debts.count(),
        },
        "recent_debts": recent_debts,
        "recent_payments": recent_payments,
        "top_debtors": top_debtors,
    }


def get_debts_report(
    business,
    *,
    date_from=None,
    date_to=None,
    group_by="day",
    direction=None,
    today=None,
):
    """Davr bo'yicha qarzlar hisoboti.

    Davr `issue_date` (qarz yuzaga kelgan sana) bo'yicha filtrlanadi.
    `series` — kun yoki oy bo'yicha qarzlar soni va summalari.
    `by_status` — bir-birini takrorlamaydigan (mutually exclusive) holatlar.
    """
    _validate_date_range(date_from, date_to)
    _validate_group_by(group_by)
    _validate_direction(direction)

    today = today or timezone.localdate()
    debts = _base_debts(business)

    if date_from:
        debts = debts.filter(issue_date__gte=date_from)
    if date_to:
        debts = debts.filter(issue_date__lte=date_to)
    if direction:
        debts = debts.filter(direction=direction)

    receivable_amount = _sum(
        debts.filter(direction=DebtDirection.RECEIVABLE), "amount"
    )
    payable_amount = _sum(
        debts.filter(direction=DebtDirection.PAYABLE), "amount"
    )

    # Faqat shu hisobot doirasidagi qarzlarga tegishli to'lovlar.
    report_debt_ids = debts.values("pk")
    paid_receivable = _payment_sum(
        Payment.objects.filter(
            debt__in=report_debt_ids,
            debt__direction=DebtDirection.RECEIVABLE,
            is_reversed=False,
        )
    )
    paid_payable = _payment_sum(
        Payment.objects.filter(
            debt__in=report_debt_ids,
            debt__direction=DebtDirection.PAYABLE,
            is_reversed=False,
        )
    )

    totals = {
        "count": debts.count(),
        "receivable_amount": receivable_amount,
        "payable_amount": payable_amount,
        "receivable_remaining": max(
            receivable_amount - paid_receivable, ZERO
        ),
        "payable_remaining": max(payable_amount - paid_payable, ZERO),
        "paid_total": paid_receivable + paid_payable,
    }

    # `due_date` NULL bo'lsa, qarz muddati o'tgan hisoblanmaydi. SQL'da
    # NULL bilan solishtirish NULL qaytaradi, shuning uchun buni aniq
    # `isnull=True` bilan yozamiz.
    not_overdue = Q(due_date__isnull=True) | Q(due_date__gte=today)
    by_status = {
        DebtStatus.OVERDUE.value: debts.filter(
            remaining__gt=ZERO,
            due_date__lt=today,
        ).count(),
        DebtStatus.PAID.value: debts.filter(remaining__lte=ZERO).count(),
        DebtStatus.PARTIAL.value: debts.filter(
            remaining__gt=ZERO,
            paid_total__gt=ZERO,
        )
        .filter(not_overdue)
        .count(),
        DebtStatus.OPEN.value: debts.filter(
            remaining__gt=ZERO,
            paid_total=ZERO,
        )
        .filter(not_overdue)
        .count(),
    }

    # Seriyalarni Python'da guruhlaymiz: Subquery asosidagi `paid_total` ni
    # SQL agregatsiyasida yig'ish ishonchsiz bo'lgani uchun.
    buckets = {}
    for row in debts.values(
        "id",
        "issue_date",
        "amount",
        "direction",
        "paid_total",
    ):
        period = _period(row["issue_date"], group_by)
        bucket = buckets.setdefault(
            period,
            {
                "period": period,
                "count": 0,
                "receivable_amount": ZERO,
                "payable_amount": ZERO,
                "paid_total": ZERO,
                "remaining_total": ZERO,
            },
        )

        amount = money(row["amount"])
        paid = money(row["paid_total"])
        remaining = max(amount - paid, ZERO)

        bucket["count"] += 1
        bucket["paid_total"] += paid
        bucket["remaining_total"] += remaining
        if row["direction"] == DebtDirection.RECEIVABLE:
            bucket["receivable_amount"] += amount
        else:
            bucket["payable_amount"] += amount

    series = [buckets[key] for key in sorted(buckets)]

    return {
        "as_of": today,
        "period": {"date_from": date_from, "date_to": date_to},
        "filters": {"group_by": group_by, "direction": direction},
        "totals": totals,
        "by_status": by_status,
        "series": series,
    }


def get_payments_report(
    business,
    *,
    date_from=None,
    date_to=None,
    group_by="day",
    method=None,
):
    """Davr bo'yicha to'lovlar hisoboti.

    `received` — "menga qarzdor" qarzlardan kelgan pul (kirim).
    `paid_out` — "men qarzdorman" qarzlar bo'yicha to'langan pul (chiqim).
    Bekor qilingan to'lovlar hisobga kirmaydi.
    """
    _validate_date_range(date_from, date_to)
    _validate_group_by(group_by)
    _validate_method(method)

    payments = Payment.objects.filter(
        debt__business=business,
        is_reversed=False,
    )

    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
    if method:
        payments = payments.filter(method=method)

    total = _sum(payments, "amount")
    received = _sum(
        payments.filter(debt__direction=DebtDirection.RECEIVABLE),
        "amount",
    )
    paid_out = _sum(
        payments.filter(debt__direction=DebtDirection.PAYABLE),
        "amount",
    )

    by_method_rows = (
        payments.values("method")
        .annotate(
            count=Count("id"),
            total=Coalesce(
                Sum("amount"),
                Value(ZERO),
                output_field=MONEY_FIELD,
            ),
        )
        .order_by("method")
    )

    by_method = []
    for row in by_method_rows:
        row = dict(row)
        row["total"] = money(row["total"])
        row["method_display"] = PaymentMethod(row["method"]).label
        by_method.append(row)

    buckets = {}
    for row in payments.values(
        "payment_date",
        "amount",
        "debt__direction",
    ):
        period = _period(row["payment_date"], group_by)
        bucket = buckets.setdefault(
            period,
            {
                "period": period,
                "count": 0,
                "total": ZERO,
                "received": ZERO,
                "paid_out": ZERO,
            },
        )

        amount = money(row["amount"])
        bucket["count"] += 1
        bucket["total"] += amount
        if row["debt__direction"] == DebtDirection.RECEIVABLE:
            bucket["received"] += amount
        else:
            bucket["paid_out"] += amount

    series = [buckets[key] for key in sorted(buckets)]

    return {
        "period": {"date_from": date_from, "date_to": date_to},
        "filters": {"group_by": group_by, "method": method},
        "totals": {
            "count": payments.count(),
            "total": total,
            "received": received,
            "paid_out": paid_out,
        },
        "by_method": by_method,
        "series": series,
    }


def get_overdue_report(business, *, as_of=None, direction=None):
    """Muddati o'tgan va qoldig'i bor qarzlar ro'yxati."""
    as_of = as_of or timezone.localdate()
    _validate_direction(direction)

    overdue_debts = _base_debts(business).filter(
        remaining__gt=ZERO,
        due_date__lt=as_of,
    )
    if direction:
        overdue_debts = overdue_debts.filter(direction=direction)

    receivable_amount = _sum(
        overdue_debts.filter(direction=DebtDirection.RECEIVABLE),
        "amount",
    )
    payable_amount = _sum(
        overdue_debts.filter(direction=DebtDirection.PAYABLE),
        "amount",
    )

    receivable_paid = _payment_sum(
        Payment.objects.filter(
            debt__in=overdue_debts.filter(
                direction=DebtDirection.RECEIVABLE
            ).values("pk"),
            is_reversed=False,
        )
    )
    payable_paid = _payment_sum(
        Payment.objects.filter(
            debt__in=overdue_debts.filter(
                direction=DebtDirection.PAYABLE
            ).values("pk"),
            is_reversed=False,
        )
    )

    totals = {
        "count": overdue_debts.count(),
        "receivable": max(receivable_amount - receivable_paid, ZERO),
        "payable": max(payable_amount - payable_paid, ZERO),
    }

    items = list(
        overdue_debts.select_related("contact").order_by("due_date", "id")
    )
    for debt in items:
        debt.days_overdue = (as_of - debt.due_date).days

    return {
        "as_of": as_of,
        "filters": {"direction": direction},
        "totals": totals,
        "items": items,
    }
