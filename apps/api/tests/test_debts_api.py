from datetime import timedelta

from django.urls import reverse

from apps.api.tests.base import ApiTestBase
from apps.debts.services import add_payment
from apps.testing import create_debt


class DebtApiTests(ApiTestBase):
    def debt_payload(self, **overrides):
        payload = {
            "contact": self.contact.id,
            "direction": "receivable",
            "amount": "1000000.00",
            "issue_date": str(self.today),
            "due_date": str(self.today + timedelta(days=30)),
            "reason": "Sotuv",
            "note": "",
        }
        payload.update(overrides)
        return payload

    def test_create_debt_returns_computed_fields_as_strings(self):
        response = self.client.post(
            reverse("api:debt-list"),
            self.debt_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["contact"], self.contact.id)
        self.assertEqual(data["contact_name"], "Ali")
        self.assertEqual(data["amount"], "1000000.00")
        self.assertEqual(data["paid_total"], "0.00")
        self.assertEqual(data["remaining"], "1000000.00")
        self.assertEqual(data["status"], "open")
        self.assertEqual(data["display_status"], "open")
        self.assertFalse(data["is_overdue"])
        self.assertEqual(data["days_overdue"], 0)
        self.assertFalse(data["is_archived"])

        from apps.debts.models import Debt

        debt = Debt.objects.get(pk=data["id"])
        self.assertEqual(debt.business_id, self.business.id)
        self.assertEqual(debt.created_by_id, self.user.id)

    def test_create_debt_with_other_tenant_contact_rejected(self):
        _, _, other_contact = self.create_other_business()

        response = self.client.post(
            reverse("api:debt-list"),
            self.debt_payload(contact=other_contact.id),
            format="json",
        )

        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("contact", error["fields"])

    def test_create_debt_due_before_issue_rejected(self):
        response = self.client.post(
            reverse("api:debt-list"),
            self.debt_payload(
                issue_date=str(self.today),
                due_date=str(self.today - timedelta(days=1)),
            ),
            format="json",
        )

        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("due_date", error["fields"])

    def test_list_excludes_archived_by_default(self):
        self.make_debt(amount="1000000.00")
        self.make_debt(amount="2000000.00", is_archived=True)

        default = self.client.get(reverse("api:debt-list"))
        all_items = self.client.get(
            reverse("api:debt-list"), {"archived": "all"}
        )
        archived_only = self.client.get(
            reverse("api:debt-list"), {"archived": "true"}
        )

        self.assertEqual(default.json()["count"], 1)
        self.assertEqual(all_items.json()["count"], 2)
        self.assertEqual(archived_only.json()["count"], 1)
        self.assertTrue(archived_only.json()["results"][0]["is_archived"])

    def test_list_is_tenant_scoped(self):
        _, other_business, other_contact = self.create_other_business()
        create_debt(
            other_business,
            other_contact,
            amount="5000000.00",
            issue_date=self.today,
            due_date=self.today + timedelta(days=10),
        )
        self.make_debt(amount="1000000.00")

        response = self.client.get(reverse("api:debt-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["amount"], "1000000.00"
        )

    def test_status_filter(self):
        open_debt = self.make_debt(
            amount="1000000.00",
            due_date=self.today + timedelta(days=10),
        )
        partial_debt = self.make_debt(
            amount="500000.00",
            due_date=self.today + timedelta(days=10),
        )
        add_payment(partial_debt, amount="200000.00", user=self.user)
        paid_debt = self.make_debt(
            amount="300000.00",
            due_date=self.today + timedelta(days=10),
        )
        add_payment(paid_debt, amount="300000.00", user=self.user)

        for status, expected_id in (
            ("open", open_debt.id),
            ("partial", partial_debt.id),
            ("paid", paid_debt.id),
        ):
            with self.subTest(status=status):
                response = self.client.get(
                    reverse("api:debt-list"), {"status": status}
                )
                self.assertEqual(response.status_code, 200)
                results = response.json()["results"]
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]["id"], expected_id)

    def test_overdue_filter(self):
        overdue = self.make_debt(
            amount="1000000.00",
            issue_date=self.today - timedelta(days=10),
            due_date=self.today - timedelta(days=5),
        )
        self.make_debt(
            amount="500000.00",
            due_date=self.today + timedelta(days=5),
        )

        response = self.client.get(
            reverse("api:debt-list"), {"status": "overdue"}
        )

        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], overdue.id)
        self.assertEqual(results[0]["display_status"], "overdue")
        self.assertTrue(results[0]["is_overdue"])
        self.assertEqual(results[0]["days_overdue"], 5)

    def test_direction_filter(self):
        self.make_debt(direction="receivable")
        self.make_debt(direction="payable")

        response = self.client.get(
            reverse("api:debt-list"), {"direction": "payable"}
        )

        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["direction"], "payable"
        )

    def test_detail_other_tenant_returns_404(self):
        _, other_business, other_contact = self.create_other_business()
        other_debt = create_debt(
            other_business,
            other_contact,
            amount="5000000.00",
            issue_date=self.today,
        )

        response = self.client.get(
            reverse("api:debt-detail", args=[other_debt.id])
        )

        self.assert_error(response, code="not_found", status_code=404)

    def test_patch_amount_without_payments_allowed(self):
        debt = self.make_debt()

        response = self.client.patch(
            reverse("api:debt-detail", args=[debt.id]),
            {"amount": "1200000.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["amount"], "1200000.00")
        self.assertEqual(response.json()["remaining"], "1200000.00")

    def test_patch_financial_fields_locked_after_payment(self):
        debt = self.make_debt()
        add_payment(debt, amount="200000.00", user=self.user)

        response = self.client.patch(
            reverse("api:debt-detail", args=[debt.id]),
            {"amount": "1500000.00"},
            format="json",
        )

        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("amount", error["fields"])

    def test_patch_due_date_after_payment_allowed(self):
        debt = self.make_debt()
        add_payment(debt, amount="200000.00", user=self.user)
        new_due = self.today + timedelta(days=60)

        response = self.client.patch(
            reverse("api:debt-detail", args=[debt.id]),
            {"due_date": str(new_due), "note": "Muddat uzaytirildi"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["due_date"], str(new_due))

    def test_delete_debt_without_payments(self):
        debt = self.make_debt()

        response = self.client.delete(
            reverse("api:debt-detail", args=[debt.id])
        )

        self.assertEqual(response.status_code, 204)

    def test_delete_debt_with_payments_returns_conflict(self):
        debt = self.make_debt()
        add_payment(debt, amount="200000.00", user=self.user)

        response = self.client.delete(
            reverse("api:debt-detail", args=[debt.id])
        )

        self.assert_error(
            response, code="debt_has_payments", status_code=409
        )

    def test_has_payments_flag(self):
        debt = self.make_debt()

        detail = self.client.get(
            reverse("api:debt-detail", args=[debt.id])
        ).json()
        self.assertFalse(detail["has_payments"])

        add_payment(debt, amount="100000.00", user=self.user)

        detail = self.client.get(
            reverse("api:debt-detail", args=[debt.id])
        ).json()
        self.assertTrue(detail["has_payments"])

        listing = self.client.get(reverse("api:debt-list")).json()
        self.assertTrue(listing["results"][0]["has_payments"])

    def test_archive_and_unarchive(self):
        debt = self.make_debt()

        archived = self.client.post(
            reverse("api:debt-archive", args=[debt.id])
        )
        self.assertEqual(archived.status_code, 200, archived.content)
        self.assertTrue(archived.json()["is_archived"])

        restored = self.client.post(
            reverse("api:debt-unarchive", args=[debt.id])
        )
        self.assertEqual(restored.status_code, 200, restored.content)
        self.assertFalse(restored.json()["is_archived"])

    def test_search_by_contact_or_reason(self):
        self.make_debt()
        self.make_debt(contact=self.contact, amount="200000.00")

        response = self.client.get(
            reverse("api:debt-list"), {"search": "Ali"}
        )

        self.assertEqual(response.json()["count"], 2)

    def test_invalid_status_query_returns_400(self):
        response = self.client.get(
            reverse("api:debt-list"), {"status": "unknown"}
        )

        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("status", error["fields"])
