from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.debts.choices import DebtDirection, DebtStatus, PaymentMethod
from apps.debts.exceptions import (
    DebtHasPaymentsError,
    InvalidPaymentAmountError,
    InvalidPaymentMethodError,
    OverpaymentError,
    PaymentAlreadyReversedError,
    ReversalReasonRequiredError,
)
from apps.debts.models import Debt, Payment
from apps.debts.services import (
    add_payment,
    annotate_debt_totals,
    archive_debt,
    build_debt_summary,
    can_delete_debt,
    delete_debt,
    filter_debts_by_status,
    get_contact_debt_summary,
    get_debt_summary,
    get_paid_total,
    reverse_payment,
)
from apps.testing import create_business_user, create_contact, create_debt


class DebtServiceTests(TestCase):
    def setUp(self):
        self.today = date(2026, 11, 19)
        self.user, self.business = create_business_user()
        self.contact = create_contact(self.business, name="Ali")
        self.debt = create_debt(
            self.business,
            self.contact,
            amount="1000000.00",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 12, 1),
        )

    def test_initial_summary_is_open(self):
        summary = get_debt_summary(self.debt, today=self.today)

        self.assertEqual(summary["paid_total"], Decimal("0.00"))
        self.assertEqual(summary["remaining"], Decimal("1000000.00"))
        self.assertEqual(summary["status"], DebtStatus.OPEN)
        self.assertEqual(summary["display_status"], DebtStatus.OPEN)
        self.assertFalse(summary["is_overdue"])

    def test_partial_payment(self):
        payment = add_payment(
            self.debt,
            amount="200000.00",
            payment_date=date(2026, 11, 5),
            user=self.user,
        )
        summary = get_debt_summary(self.debt, today=self.today)

        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(payment.created_by, self.user)
        self.assertEqual(summary["paid_total"], Decimal("200000.00"))
        self.assertEqual(summary["remaining"], Decimal("800000.00"))
        self.assertEqual(summary["status"], DebtStatus.PARTIAL)
        self.assertFalse(summary["is_overdue"])

    def test_full_payment_is_paid_and_not_overdue(self):
        add_payment(
            self.debt,
            amount="1000000.00",
            payment_date=date(2026, 11, 1),
            user=self.user,
        )
        self.debt.due_date = date(2026, 11, 10)
        self.debt.save(update_fields=["due_date"])

        summary = get_debt_summary(self.debt, today=self.today)

        self.assertEqual(summary["paid_total"], Decimal("1000000.00"))
        self.assertEqual(summary["remaining"], Decimal("0.00"))
        self.assertEqual(summary["status"], DebtStatus.PAID)
        self.assertEqual(summary["display_status"], DebtStatus.PAID)
        self.assertFalse(summary["is_overdue"])

    def test_multiple_payments_calculate_remaining(self):
        add_payment(
            self.debt, amount="200000.00", payment_date=date(2026, 11, 5)
        )
        add_payment(
            self.debt, amount="300000.00", payment_date=date(2026, 11, 6)
        )

        summary = get_debt_summary(self.debt, today=self.today)
        self.assertEqual(summary["paid_total"], Decimal("500000.00"))
        self.assertEqual(summary["remaining"], Decimal("500000.00"))
        self.assertEqual(summary["status"], DebtStatus.PARTIAL)

    def test_overpayment_rejected(self):
        with self.assertRaises(OverpaymentError) as ctx:
            add_payment(self.debt, amount="1000000.01")

        self.assertEqual(ctx.exception.remaining, Decimal("1000000.00"))
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(get_paid_total(self.debt), Decimal("0.00"))

    def test_overpayment_after_partial_payment(self):
        add_payment(self.debt, amount="800000.00")

        with self.assertRaises(OverpaymentError) as ctx:
            add_payment(self.debt, amount="200000.01")

        self.assertEqual(ctx.exception.remaining, Decimal("200000.00"))
        self.assertEqual(Payment.objects.count(), 1)

    def test_payment_on_fully_paid_debt_rejected(self):
        add_payment(self.debt, amount="1000000.00")

        with self.assertRaises(OverpaymentError) as ctx:
            add_payment(self.debt, amount="0.01")

        self.assertEqual(ctx.exception.remaining, Decimal("0.00"))
        self.assertEqual(Payment.objects.count(), 1)

    def test_invalid_payment_amounts_rejected(self):
        for amount in (0, "-1", "abc", "100.001", None):
            with self.subTest(amount=amount):
                with self.assertRaises(InvalidPaymentAmountError):
                    add_payment(self.debt, amount=amount)

        self.assertEqual(Payment.objects.count(), 0)

    def test_invalid_payment_method_rejected(self):
        with self.assertRaises(InvalidPaymentMethodError):
            add_payment(self.debt, amount="100000.00", method="crypto")

        self.assertEqual(Payment.objects.count(), 0)

    def test_reverse_payment_restores_remaining(self):
        payment = add_payment(
            self.debt,
            amount="200000.00",
            payment_date=date(2026, 11, 5),
            user=self.user,
        )

        reversed_payment = reverse_payment(
            payment,
            reason="Xato kiritilgan",
            user=self.user,
        )
        reversed_payment.refresh_from_db()
        summary = get_debt_summary(self.debt, today=self.today)

        self.assertTrue(reversed_payment.is_reversed)
        self.assertIsNotNone(reversed_payment.reversed_at)
        self.assertEqual(reversed_payment.reversal_reason, "Xato kiritilgan")
        self.assertEqual(reversed_payment.reversed_by, self.user)
        self.assertEqual(summary["paid_total"], Decimal("0.00"))
        self.assertEqual(summary["remaining"], Decimal("1000000.00"))
        # Tarix yo'qolmaydi: yozuv bazada qoladi.
        self.assertEqual(Payment.objects.count(), 1)

    def test_reverse_twice_rejected(self):
        payment = add_payment(self.debt, amount="200000.00")
        reverse_payment(payment, reason="birinchi bekor qilish")

        with self.assertRaises(PaymentAlreadyReversedError):
            reverse_payment(payment, reason="ikkinchi urinish")

    def test_reverse_requires_reason(self):
        payment = add_payment(self.debt, amount="200000.00")

        with self.assertRaises(ReversalReasonRequiredError):
            reverse_payment(payment, reason="   ")

        payment.refresh_from_db()
        self.assertFalse(payment.is_reversed)

    def test_overdue_detection(self):
        self.debt.due_date = date(2026, 11, 10)
        self.debt.save(update_fields=["due_date"])

        summary = get_debt_summary(self.debt, today=self.today)

        self.assertTrue(summary["is_overdue"])
        self.assertEqual(summary["display_status"], DebtStatus.OVERDUE)
        self.assertEqual(summary["days_overdue"], 9)
        # Bazaviy holat o'zgarmaydi: qarz hali ochiq.
        self.assertEqual(summary["status"], DebtStatus.OPEN)

    def test_paid_debt_is_never_overdue(self):
        add_payment(self.debt, amount="1000000.00")
        self.debt.due_date = date(2026, 11, 10)
        self.debt.save(update_fields=["due_date"])

        summary = get_debt_summary(self.debt, today=self.today)

        self.assertEqual(summary["status"], DebtStatus.PAID)
        self.assertFalse(summary["is_overdue"])
        self.assertEqual(summary["display_status"], DebtStatus.PAID)

    def test_delete_debt_without_payments(self):
        debt_id = self.debt.pk
        self.assertTrue(can_delete_debt(self.debt))
        delete_debt(self.debt)
        self.assertFalse(Debt.objects.filter(pk=debt_id).exists())

    def test_delete_debt_with_payments_rejected(self):
        add_payment(self.debt, amount="200000.00")
        debt_id = self.debt.pk

        self.assertFalse(can_delete_debt(self.debt))
        with self.assertRaises(DebtHasPaymentsError):
            delete_debt(self.debt)

        self.assertTrue(Debt.objects.filter(pk=debt_id).exists())

    def test_archive_and_unarchive_debt(self):
        archive_debt(self.debt, archived=True)
        self.debt.refresh_from_db()
        self.assertTrue(self.debt.is_archived)

        archive_debt(self.debt, archived=False)
        self.debt.refresh_from_db()
        self.assertFalse(self.debt.is_archived)

    def test_contact_summary_keeps_directions_separate(self):
        payable_debt = create_debt(
            self.business,
            self.contact,
            amount="300000.00",
            direction=DebtDirection.PAYABLE,
            issue_date=date(2026, 11, 1),
            due_date=date(2026, 12, 1),
        )
        add_payment(payable_debt, amount="100000.00")

        summary = get_contact_debt_summary(self.contact)

        self.assertEqual(summary["receivable"]["count"], 1)
        self.assertEqual(
            summary["receivable"]["total_amount"], Decimal("1000000.00")
        )
        self.assertEqual(
            summary["receivable"]["remaining"], Decimal("1000000.00")
        )
        self.assertEqual(summary["payable"]["count"], 1)
        self.assertEqual(
            summary["payable"]["total_amount"], Decimal("300000.00")
        )
        self.assertEqual(
            summary["payable"]["paid_total"], Decimal("100000.00")
        )
        self.assertEqual(
            summary["payable"]["remaining"], Decimal("200000.00")
        )
        self.assertEqual(summary["total_count"], 2)

    def test_filter_by_status(self):
        partial_debt = create_debt(
            self.business,
            self.contact,
            amount="500000.00",
            issue_date=date(2026, 11, 1),
            due_date=date(2026, 12, 1),
        )
        add_payment(partial_debt, amount="200000.00")

        paid_debt = create_debt(
            self.business,
            self.contact,
            amount="300000.00",
            issue_date=date(2026, 11, 1),
            due_date=date(2026, 12, 1),
        )
        add_payment(paid_debt, amount="300000.00")

        overdue_debt = create_debt(
            self.business,
            self.contact,
            amount="100000.00",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 11, 10),
        )

        queryset = Debt.objects.filter(business=self.business)

        self.assertEqual(
            filter_debts_by_status(
                queryset, DebtStatus.OPEN, today=self.today
            ).count(),
            2,  # self.debt + overdue_debt
        )
        self.assertEqual(
            filter_debts_by_status(
                queryset, DebtStatus.PARTIAL, today=self.today
            ).count(),
            1,
        )
        self.assertEqual(
            filter_debts_by_status(
                queryset, DebtStatus.PAID, today=self.today
            ).count(),
            1,
        )
        self.assertEqual(
            filter_debts_by_status(
                queryset, DebtStatus.OVERDUE, today=self.today
            ).count(),
            1,
        )

        with self.assertRaises(ValueError):
            filter_debts_by_status(queryset, "unknown", today=self.today)

    def test_annotate_totals_matches_summary(self):
        add_payment(self.debt, amount="200000.00")

        annotated = annotate_debt_totals(
            Debt.objects.filter(pk=self.debt.pk)
        ).get()
        summary = get_debt_summary(annotated, today=self.today)

        self.assertEqual(annotated.paid_total, Decimal("200000.00"))
        self.assertEqual(annotated.remaining, Decimal("800000.00"))
        self.assertEqual(summary["paid_total"], annotated.paid_total)
        self.assertEqual(summary["remaining"], annotated.remaining)

    def test_cannot_pay_another_business_debt(self):
        other_user, _ = create_business_user(
            username="other",
            phone="+998902223344",
            email="other@example.com",
            business_name="Boshqa biznes",
        )

        with self.assertRaises(PermissionError):
            add_payment(
                self.debt,
                amount="100000.00",
                user=other_user,
            )

        self.assertEqual(Payment.objects.count(), 0)

    def test_build_debt_summary_handles_zero_and_negative_remaining(self):
        # Hatto noto'g'ri ma'lumot bo'lsa ham qoldiq manfiy ko'rsatilmaydi.
        summary = build_debt_summary(
            amount=Decimal("100.00"),
            paid_total=Decimal("150.00"),
            due_date=None,
            today=self.today,
        )
        self.assertEqual(summary["remaining"], Decimal("0.00"))
        self.assertEqual(summary["status"], DebtStatus.PAID)
