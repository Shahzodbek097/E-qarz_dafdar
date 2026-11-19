from django.urls import reverse

from apps.api.tests.base import ApiTestBase
from apps.debts.services import add_payment, reverse_payment
from apps.testing import create_debt


class PaymentApiTests(ApiTestBase):
    def test_create_payment_updates_debt_totals(self):
        debt = self.make_debt(amount="1000000.00")

        response = self.client.post(
            reverse("api:debt-payments", args=[debt.id]),
            {
                "amount": "200000.00",
                "method": "cash",
                "note": "Birinchi to'lov",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["debt"], debt.id)
        self.assertEqual(data["debt_contact_name"], "Ali")
        self.assertEqual(data["amount"], "200000.00")
        self.assertEqual(data["method"], "cash")
        self.assertEqual(data["method_display"], "Naqd")
        self.assertFalse(data["is_reversed"])
        self.assertIsNone(data["reversed_by"])
        self.assertEqual(data["created_by"], "owner")

        detail = self.client.get(
            reverse("api:debt-detail", args=[debt.id])
        ).json()
        self.assertEqual(detail["paid_total"], "200000.00")
        self.assertEqual(detail["remaining"], "800000.00")
        self.assertEqual(detail["status"], "partial")

    def test_overpayment_returns_conflict(self):
        debt = self.make_debt(amount="1000000.00")

        response = self.client.post(
            reverse("api:debt-payments", args=[debt.id]),
            {"amount": "1000000.01"},
            format="json",
        )

        error = self.assert_error(
            response, code="overpayment", status_code=409
        )
        self.assertIn("1000000.00", error["message"])

    def test_invalid_amount_returns_field_error(self):
        debt = self.make_debt()

        for amount in ("0", "-5", "abc"):
            with self.subTest(amount=amount):
                response = self.client.post(
                    reverse("api:debt-payments", args=[debt.id]),
                    {"amount": amount},
                    format="json",
                )
                error = self.assert_error(
                    response,
                    code="validation_error",
                    status_code=400,
                )
                self.assertIn("amount", error["fields"])

    def test_invalid_method_returns_field_error(self):
        debt = self.make_debt()

        response = self.client.post(
            reverse("api:debt-payments", args=[debt.id]),
            {"amount": "100000.00", "method": "crypto"},
            format="json",
        )

        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("method", error["fields"])

    def test_create_payment_on_other_tenant_debt_returns_404(self):
        _, other_business, other_contact = self.create_other_business()
        other_debt = create_debt(
            other_business,
            other_contact,
            amount="1000000.00",
            issue_date=self.today,
        )

        response = self.client.post(
            reverse("api:debt-payments", args=[other_debt.id]),
            {"amount": "100000.00"},
            format="json",
        )

        self.assert_error(response, code="not_found", status_code=404)

    def test_payment_list_is_tenant_scoped(self):
        own_debt = self.make_debt()
        add_payment(own_debt, amount="200000.00", user=self.user)

        other_user, other_business, other_contact = (
            self.create_other_business()
        )
        other_debt = create_debt(
            other_business,
            other_contact,
            amount="1000000.00",
            issue_date=self.today,
        )
        add_payment(other_debt, amount="100000.00", user=other_user)

        response = self.client.get(reverse("api:payment-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["debt"], own_debt.id
        )

    def test_payment_list_filters(self):
        debt = self.make_debt(amount="1000000.00")
        add_payment(
            debt, amount="100000.00", method="cash", user=self.user
        )
        bank = add_payment(
            debt, amount="200000.00", method="bank", user=self.user
        )
        reversed_payment = add_payment(
            debt, amount="50000.00", method="cash", user=self.user
        )

        reverse_payment(reversed_payment, reason="Xato", user=self.user)

        by_method = self.client.get(
            reverse("api:payment-list"), {"method": "bank"}
        )
        self.assertEqual(by_method.json()["count"], 1)
        self.assertEqual(by_method.json()["results"][0]["id"], bank.id)

        active = self.client.get(
            reverse("api:payment-list"), {"is_reversed": "false"}
        )
        self.assertEqual(active.json()["count"], 2)

        by_debt = self.client.get(
            reverse("api:payment-list"), {"debt": debt.id}
        )
        self.assertEqual(by_debt.json()["count"], 3)

        by_date = self.client.get(
            reverse("api:payment-list"),
            {"date_from": str(self.today), "date_to": str(self.today)},
        )
        self.assertEqual(by_date.json()["count"], 3)

    def test_reverse_payment_restores_remaining(self):
        debt = self.make_debt(amount="1000000.00")
        payment = add_payment(
            debt, amount="200000.00", user=self.user
        )

        response = self.client.post(
            reverse("api:payment-reverse", args=[payment.id]),
            {"reason": "Xato kiritilgan"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertTrue(data["is_reversed"])
        self.assertEqual(data["reversal_reason"], "Xato kiritilgan")
        self.assertEqual(data["reversed_by"], "owner")
        self.assertIsNotNone(data["reversed_at"])

        detail = self.client.get(
            reverse("api:debt-detail", args=[debt.id])
        ).json()
        self.assertEqual(detail["paid_total"], "0.00")
        self.assertEqual(detail["remaining"], "1000000.00")
        self.assertEqual(detail["status"], "open")

    def test_reverse_requires_reason(self):
        debt = self.make_debt()
        payment = add_payment(
            debt, amount="200000.00", user=self.user
        )

        response = self.client.post(
            reverse("api:payment-reverse", args=[payment.id]),
            {"reason": "   "},
            format="json",
        )

        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("reason", error["fields"])

    def test_reverse_twice_returns_conflict(self):
        debt = self.make_debt()
        payment = add_payment(
            debt, amount="200000.00", user=self.user
        )
        self.client.post(
            reverse("api:payment-reverse", args=[payment.id]),
            {"reason": "Birinchi"},
            format="json",
        )

        response = self.client.post(
            reverse("api:payment-reverse", args=[payment.id]),
            {"reason": "Ikkinchi"},
            format="json",
        )

        self.assert_error(
            response,
            code="payment_already_reversed",
            status_code=409,
        )

    def test_reverse_other_tenant_payment_returns_404(self):
        other_user, other_business, other_contact = (
            self.create_other_business()
        )
        other_debt = create_debt(
            other_business,
            other_contact,
            amount="1000000.00",
            issue_date=self.today,
        )
        other_payment = add_payment(
            other_debt, amount="100000.00", user=other_user
        )

        response = self.client.post(
            reverse("api:payment-reverse", args=[other_payment.id]),
            {"reason": "Xato"},
            format="json",
        )

        self.assert_error(response, code="not_found", status_code=404)
