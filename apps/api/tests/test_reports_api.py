from datetime import timedelta

from django.urls import reverse

from apps.api.tests.base import ApiTestBase
from apps.debts.services import add_payment
from apps.testing import create_contact, create_debt


class ReportApiTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.contact_b = create_contact(self.business, name="Vali")

        # Muddati o'tgan, qisman to'langan "menga qarzdor".
        self.r1 = self.make_debt(
            amount="1000000.00",
            issue_date=self.today - timedelta(days=20),
            due_date=self.today - timedelta(days=5),
        )
        add_payment(
            self.r1,
            amount="200000.00",
            method="cash",
            user=self.user,
        )

        # To'liq to'langan "menga qarzdor".
        self.r2 = self.make_debt(
            amount="500000.00",
            due_date=self.today + timedelta(days=10),
        )
        add_payment(
            self.r2,
            amount="500000.00",
            method="bank",
            user=self.user,
        )

        # Ochiq "men qarzdorman".
        self.p1 = self.make_debt(
            amount="300000.00",
            direction="payable",
            due_date=self.today + timedelta(days=10),
        )

    def test_dashboard_totals_and_strings(self):
        response = self.client.get(reverse("api:report-dashboard"))

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        totals = data["totals"]

        self.assertEqual(totals["receivable"], "800000.00")
        self.assertEqual(totals["payable"], "300000.00")
        self.assertEqual(totals["overdue_receivable"], "800000.00")
        self.assertEqual(totals["overdue_payable"], "0.00")
        self.assertEqual(totals["paid_receivable"], "700000.00")
        self.assertEqual(totals["paid_payable"], "0.00")
        self.assertEqual(totals["paid_total"], "700000.00")
        self.assertEqual(totals["active_debts_count"], 2)
        self.assertEqual(totals["overdue_count"], 1)

        self.assertEqual(len(data["recent_debts"]), 3)
        self.assertEqual(len(data["recent_payments"]), 2)
        self.assertEqual(data["top_debtors"][0]["name"], "Ali")
        self.assertEqual(
            data["top_debtors"][0]["remaining"], "800000.00"
        )

    def test_dashboard_is_tenant_scoped(self):
        _, other_business, other_contact = self.create_other_business()
        create_debt(
            other_business,
            other_contact,
            amount="5000000.00",
            issue_date=self.today - timedelta(days=10),
            due_date=self.today - timedelta(days=5),
        )

        response = self.client.get(reverse("api:report-dashboard"))

        self.assertEqual(
            response.json()["totals"]["receivable"], "800000.00"
        )
        self.assertEqual(response.json()["totals"]["overdue_count"], 1)

    def test_debts_report(self):
        response = self.client.get(
            reverse("api:report-debts"),
            {
                "date_from": str(self.today - timedelta(days=30)),
                "date_to": str(self.today),
                "group_by": "day",
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        totals = data["totals"]

        self.assertEqual(totals["count"], 3)
        self.assertEqual(totals["receivable_amount"], "1500000.00")
        self.assertEqual(totals["payable_amount"], "300000.00")
        self.assertEqual(totals["receivable_remaining"], "800000.00")
        self.assertEqual(totals["payable_remaining"], "300000.00")
        self.assertEqual(totals["paid_total"], "700000.00")

        self.assertEqual(data["by_status"]["overdue"], 1)
        self.assertEqual(data["by_status"]["paid"], 1)
        self.assertEqual(data["by_status"]["partial"], 0)
        self.assertEqual(data["by_status"]["open"], 1)

        self.assertEqual(len(data["series"]), 2)
        earlier, current = data["series"]

        self.assertEqual(earlier["count"], 1)
        self.assertEqual(earlier["receivable_amount"], "1000000.00")
        self.assertEqual(earlier["paid_total"], "200000.00")
        self.assertEqual(earlier["remaining_total"], "800000.00")

        self.assertEqual(current["count"], 2)
        self.assertEqual(current["receivable_amount"], "500000.00")
        self.assertEqual(current["payable_amount"], "300000.00")
        self.assertEqual(current["paid_total"], "500000.00")
        self.assertEqual(current["remaining_total"], "300000.00")

    def test_debts_report_direction_filter(self):
        response = self.client.get(
            reverse("api:report-debts"),
            {"direction": "payable"},
        )

        data = response.json()
        self.assertEqual(data["totals"]["count"], 1)
        self.assertEqual(data["totals"]["receivable_amount"], "0.00")
        self.assertEqual(data["totals"]["payable_amount"], "300000.00")

    def test_payments_report(self):
        response = self.client.get(
            reverse("api:report-payments"),
            {
                "date_from": str(self.today),
                "date_to": str(self.today),
            },
        )

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        totals = data["totals"]

        self.assertEqual(totals["count"], 2)
        self.assertEqual(totals["total"], "700000.00")
        self.assertEqual(totals["received"], "700000.00")
        self.assertEqual(totals["paid_out"], "0.00")

        methods = {
            row["method"]: row for row in data["by_method"]
        }
        self.assertEqual(methods["cash"]["total"], "200000.00")
        self.assertEqual(methods["bank"]["total"], "500000.00")

        self.assertEqual(len(data["series"]), 1)
        self.assertEqual(data["series"][0]["total"], "700000.00")

    def test_overdue_report(self):
        response = self.client.get(
            reverse("api:report-overdue"),
            {"as_of": str(self.today)},
        )

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        self.assertEqual(data["totals"]["count"], 1)
        self.assertEqual(data["totals"]["receivable"], "800000.00")
        self.assertEqual(data["totals"]["payable"], "0.00")
        self.assertEqual(len(data["items"]), 1)

        item = data["items"][0]
        self.assertEqual(item["id"], self.r1.id)
        self.assertEqual(item["days_overdue"], 5)
        self.assertTrue(item["is_overdue"])
        self.assertEqual(item["display_status"], "overdue")

    def test_invalid_report_query_returns_400(self):
        response = self.client.get(
            reverse("api:report-debts"), {"group_by": "week"}
        )
        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("group_by", error["fields"])

        response = self.client.get(
            reverse("api:report-payments"),
            {
                "date_from": str(self.today),
                "date_to": str(self.today - timedelta(days=1)),
            },
        )
        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("date_to", error["fields"])
