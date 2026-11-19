from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.debts.choices import DebtDirection, PaymentMethod
from apps.debts.services import add_payment, reverse_payment
from apps.reports.services import (
    get_dashboard_summary,
    get_debts_report,
    get_overdue_report,
    get_payments_report,
)
from apps.testing import create_business_user, create_contact, create_debt


class ReportServiceTests(TestCase):
    def setUp(self):
        self.today = date(2026, 11, 19)
        self.user, self.business = create_business_user()

        self.contact_a = create_contact(
            self.business, name="Ali", phone="+998901112233"
        )
        self.contact_b = create_contact(
            self.business, name="Vali", phone="+998901112244"
        )

        # 1) Muddati o'tgan, qisman to'langan "menga qarzdor"
        self.r1 = create_debt(
            self.business,
            self.contact_a,
            amount="1000000.00",
            direction=DebtDirection.RECEIVABLE,
            issue_date=date(2026, 11, 1),
            due_date=date(2026, 11, 10),
        )
        # 2) To'liq to'langan "menga qarzdor"
        self.r2 = create_debt(
            self.business,
            self.contact_b,
            amount="500000.00",
            direction=DebtDirection.RECEIVABLE,
            issue_date=date(2026, 11, 15),
            due_date=date(2026, 12, 1),
        )
        # 3) Ochiq "men qarzdorman" (muddati hali o'tmagan)
        self.p1 = create_debt(
            self.business,
            self.contact_b,
            amount="300000.00",
            direction=DebtDirection.PAYABLE,
            issue_date=date(2026, 11, 10),
            due_date=date(2026, 11, 20),
        )
        # 4) O'tgan oyda to'liq to'langan "men qarzdorman"
        self.p2 = create_debt(
            self.business,
            self.contact_a,
            amount="100000.00",
            direction=DebtDirection.PAYABLE,
            issue_date=date(2026, 10, 1),
            due_date=date(2026, 10, 15),
        )
        # 5) Bugun muddati tugaydigan, hali o'tmagan qarz
        self.r3 = create_debt(
            self.business,
            self.contact_b,
            amount="200000.00",
            direction=DebtDirection.RECEIVABLE,
            issue_date=date(2026, 11, 18),
            due_date=date(2026, 11, 19),
        )
        # 6) Arxivlangan qarz hisobotlarga kirmasligi kerak
        self.archived = create_debt(
            self.business,
            self.contact_a,
            amount="999000.00",
            direction=DebtDirection.RECEIVABLE,
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 1),
            is_archived=True,
        )

        self.pay_r1 = add_payment(
            self.r1,
            amount="200000.00",
            payment_date=date(2026, 11, 5),
            method=PaymentMethod.CASH,
            user=self.user,
        )
        self.pay_r2 = add_payment(
            self.r2,
            amount="500000.00",
            payment_date=date(2026, 11, 16),
            method=PaymentMethod.BANK,
            user=self.user,
        )
        self.pay_p2 = add_payment(
            self.p2,
            amount="100000.00",
            payment_date=date(2026, 10, 20),
            method=PaymentMethod.CASH,
            user=self.user,
        )

        # Bekor qilingan to'lov hisobga kirmasligi kerak.
        reversed_payment = add_payment(
            self.r1,
            amount="50000.00",
            payment_date=date(2026, 11, 6),
            method=PaymentMethod.CASH,
            user=self.user,
        )
        reverse_payment(
            reversed_payment,
            reason="Xato kiritilgan",
            user=self.user,
        )

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def test_dashboard_splits_receivable_and_payable(self):
        summary = get_dashboard_summary(self.business, today=self.today)
        totals = summary["totals"]

        self.assertEqual(totals["receivable"], Decimal("1000000.00"))
        self.assertEqual(totals["payable"], Decimal("300000.00"))
        self.assertEqual(
            totals["overdue_receivable"], Decimal("800000.00")
        )
        self.assertEqual(totals["overdue_payable"], Decimal("0.00"))
        self.assertEqual(
            totals["paid_receivable"], Decimal("700000.00")
        )
        self.assertEqual(totals["paid_payable"], Decimal("100000.00"))
        self.assertEqual(totals["paid_total"], Decimal("800000.00"))
        self.assertEqual(totals["active_debts_count"], 3)
        self.assertEqual(totals["overdue_count"], 1)

    def test_dashboard_recent_items(self):
        summary = get_dashboard_summary(self.business, today=self.today)

        self.assertEqual(len(summary["recent_debts"]), 5)
        self.assertTrue(
            all(not debt.is_archived for debt in summary["recent_debts"])
        )
        self.assertEqual(len(summary["recent_payments"]), 3)
        self.assertTrue(
            all(
                not payment.is_reversed
                for payment in summary["recent_payments"]
            )
        )

    def test_dashboard_top_debtors(self):
        summary = get_dashboard_summary(self.business, today=self.today)
        top = summary["top_debtors"]

        self.assertEqual(len(top), 2)
        self.assertEqual(top[0]["name"], "Ali")
        self.assertEqual(top[0]["remaining"], Decimal("800000.00"))
        self.assertEqual(top[1]["name"], "Vali")
        self.assertEqual(top[1]["remaining"], Decimal("200000.00"))

    def test_dashboard_is_tenant_scoped(self):
        other_user, other_business = create_business_user(
            username="other",
            phone="+998902223344",
            email="other@example.com",
            business_name="Boshqa biznes",
        )
        other_contact = create_contact(other_business, name="Boshqa mijoz")
        create_debt(
            other_business,
            other_contact,
            amount="5000000.00",
            issue_date=date(2026, 11, 1),
            due_date=date(2026, 11, 10),
        )

        summary = get_dashboard_summary(self.business, today=self.today)
        self.assertEqual(
            summary["totals"]["receivable"], Decimal("1000000.00")
        )

    # ------------------------------------------------------------------
    # Qarzlar hisoboti
    # ------------------------------------------------------------------

    def test_debts_report_totals_and_statuses(self):
        report = get_debts_report(
            self.business,
            date_from=date(2026, 11, 1),
            date_to=date(2026, 11, 30),
            today=self.today,
        )
        totals = report["totals"]

        self.assertEqual(totals["count"], 4)
        self.assertEqual(
            totals["receivable_amount"], Decimal("1700000.00")
        )
        self.assertEqual(totals["payable_amount"], Decimal("300000.00"))
        self.assertEqual(
            totals["receivable_remaining"], Decimal("1000000.00")
        )
        self.assertEqual(
            totals["payable_remaining"], Decimal("300000.00")
        )
        self.assertEqual(totals["paid_total"], Decimal("700000.00"))

        self.assertEqual(report["by_status"]["overdue"], 1)
        self.assertEqual(report["by_status"]["paid"], 1)
        self.assertEqual(report["by_status"]["partial"], 0)
        self.assertEqual(report["by_status"]["open"], 2)

    def test_debts_report_daily_series(self):
        report = get_debts_report(
            self.business,
            date_from=date(2026, 11, 1),
            date_to=date(2026, 11, 30),
            group_by="day",
            today=self.today,
        )
        series = {str(row["period"]): row for row in report["series"]}

        self.assertEqual(len(series), 4)
        self.assertEqual(
            series["2026-11-01"]["receivable_amount"],
            Decimal("1000000.00"),
        )
        self.assertEqual(
            series["2026-11-01"]["paid_total"],
            Decimal("200000.00"),
        )
        self.assertEqual(
            series["2026-11-10"]["payable_amount"],
            Decimal("300000.00"),
        )
        self.assertEqual(
            series["2026-11-15"]["paid_total"],
            Decimal("500000.00"),
        )
        self.assertEqual(
            series["2026-11-18"]["remaining_total"],
            Decimal("200000.00"),
        )

    def test_debts_report_month_grouping(self):
        report = get_debts_report(
            self.business,
            date_from=date(2026, 11, 1),
            date_to=date(2026, 11, 30),
            group_by="month",
            today=self.today,
        )

        self.assertEqual(len(report["series"]), 1)
        self.assertEqual(str(report["series"][0]["period"]), "2026-11-01")
        self.assertEqual(report["series"][0]["count"], 4)

    def test_debts_report_direction_filter(self):
        report = get_debts_report(
            self.business,
            date_from=date(2026, 11, 1),
            date_to=date(2026, 11, 30),
            direction=DebtDirection.RECEIVABLE,
            today=self.today,
        )

        self.assertEqual(report["totals"]["count"], 3)
        self.assertEqual(report["totals"]["payable_amount"], Decimal("0.00"))
        self.assertEqual(
            report["totals"]["payable_remaining"], Decimal("0.00")
        )
        self.assertEqual(report["by_status"]["open"], 1)

    def test_debts_report_invalid_input(self):
        with self.assertRaises(ValidationError):
            get_debts_report(
                self.business,
                date_from=date(2026, 12, 1),
                date_to=date(2026, 11, 1),
            )
        with self.assertRaises(ValidationError):
            get_debts_report(self.business, group_by="week")

    # ------------------------------------------------------------------
    # To'lovlar hisoboti
    # ------------------------------------------------------------------

    def test_payments_report_totals_and_methods(self):
        report = get_payments_report(
            self.business,
            date_from=date(2026, 11, 1),
            date_to=date(2026, 11, 30),
        )
        totals = report["totals"]

        self.assertEqual(totals["count"], 2)
        self.assertEqual(totals["total"], Decimal("700000.00"))
        self.assertEqual(totals["received"], Decimal("700000.00"))
        self.assertEqual(totals["paid_out"], Decimal("0.00"))

        methods = {row["method"]: row for row in report["by_method"]}
        self.assertEqual(methods["cash"]["total"], Decimal("200000.00"))
        self.assertEqual(methods["cash"]["count"], 1)
        self.assertEqual(methods["bank"]["total"], Decimal("500000.00"))
        self.assertEqual(methods["bank"]["count"], 1)

    def test_payments_report_daily_series(self):
        report = get_payments_report(
            self.business,
            date_from=date(2026, 11, 1),
            date_to=date(2026, 11, 30),
        )
        series = {str(row["period"]): row for row in report["series"]}

        self.assertEqual(len(series), 2)
        self.assertEqual(
            series["2026-11-05"]["total"], Decimal("200000.00")
        )
        self.assertEqual(
            series["2026-11-16"]["total"], Decimal("500000.00")
        )

    def test_payments_report_all_time_and_direction_split(self):
        report = get_payments_report(self.business)

        self.assertEqual(report["totals"]["count"], 3)
        self.assertEqual(report["totals"]["total"], Decimal("800000.00"))
        self.assertEqual(report["totals"]["received"], Decimal("700000.00"))
        self.assertEqual(report["totals"]["paid_out"], Decimal("100000.00"))

    def test_payments_report_excludes_reversed(self):
        report = get_payments_report(self.business)
        # 850000 emas: 50000 bekor qilingan.
        self.assertEqual(report["totals"]["total"], Decimal("800000.00"))

    def test_payments_report_method_filter(self):
        report = get_payments_report(
            self.business,
            date_from=date(2026, 11, 1),
            date_to=date(2026, 11, 30),
            method=PaymentMethod.CASH,
        )

        self.assertEqual(report["totals"]["count"], 1)
        self.assertEqual(report["totals"]["total"], Decimal("200000.00"))

    def test_payments_report_month_grouping(self):
        report = get_payments_report(
            self.business,
            date_from=date(2026, 11, 1),
            date_to=date(2026, 11, 30),
            group_by="month",
        )

        self.assertEqual(len(report["series"]), 1)
        self.assertEqual(str(report["series"][0]["period"]), "2026-11-01")
        self.assertEqual(
            report["series"][0]["total"], Decimal("700000.00")
        )

    def test_payments_report_invalid_method(self):
        with self.assertRaises(ValidationError):
            get_payments_report(self.business, method="crypto")

    # ------------------------------------------------------------------
    # Muddati o'tgan qarzlar hisoboti
    # ------------------------------------------------------------------

    def test_overdue_report(self):
        report = get_overdue_report(self.business, as_of=self.today)

        self.assertEqual(report["totals"]["count"], 1)
        self.assertEqual(
            report["totals"]["receivable"], Decimal("800000.00")
        )
        self.assertEqual(report["totals"]["payable"], Decimal("0.00"))
        self.assertEqual(len(report["items"]), 1)
        self.assertEqual(report["items"][0].pk, self.r1.pk)
        self.assertEqual(report["items"][0].days_overdue, 9)

    def test_overdue_report_as_of_later(self):
        report = get_overdue_report(
            self.business, as_of=date(2026, 11, 21)
        )

        self.assertEqual(report["totals"]["count"], 3)
        self.assertEqual(
            report["totals"]["receivable"], Decimal("1000000.00")
        )
        self.assertEqual(report["totals"]["payable"], Decimal("300000.00"))

        by_id = {debt.pk: debt for debt in report["items"]}
        self.assertEqual(by_id[self.r1.pk].days_overdue, 11)
        self.assertEqual(by_id[self.p1.pk].days_overdue, 1)
        self.assertEqual(by_id[self.r3.pk].days_overdue, 2)

    def test_overdue_report_direction_filter(self):
        report = get_overdue_report(
            self.business,
            as_of=date(2026, 11, 21),
            direction=DebtDirection.PAYABLE,
        )

        self.assertEqual(report["totals"]["count"], 1)
        self.assertEqual(report["totals"]["receivable"], Decimal("0.00"))
        self.assertEqual(report["totals"]["payable"], Decimal("300000.00"))

    def test_overdue_report_excludes_paid_and_archived(self):
        report = get_overdue_report(
            self.business, as_of=date(2026, 11, 21)
        )
        pks = {debt.pk for debt in report["items"]}

        self.assertNotIn(self.r2.pk, pks)  # to'langan
        self.assertNotIn(self.p2.pk, pks)  # to'langan
        self.assertNotIn(self.archived.pk, pks)  # arxivlangan

    def test_overdue_report_is_tenant_scoped(self):
        other_user, other_business = create_business_user(
            username="other2",
            phone="+998903334455",
            email="other2@example.com",
            business_name="Boshqa biznes 2",
        )
        other_contact = create_contact(other_business, name="Boshqa mijoz")
        create_debt(
            other_business,
            other_contact,
            amount="5000000.00",
            issue_date=date(2026, 1, 1),
            due_date=date(2026, 1, 10),
        )

        report = get_overdue_report(self.business, as_of=self.today)
        self.assertEqual(report["totals"]["count"], 1)
        self.assertEqual(
            report["totals"]["receivable"], Decimal("800000.00")
        )
