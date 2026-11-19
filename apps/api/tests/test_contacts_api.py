from django.urls import reverse

from apps.api.tests.base import ApiTestBase
from apps.debts.services import add_payment


class ContactApiTests(ApiTestBase):
    def test_list_is_tenant_scoped(self):
        _, _, other_contact = self.create_other_business()

        response = self.client.get(reverse("api:contact-list"))

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.json()["results"]]
        self.assertEqual(ids, [self.contact.id])
        self.assertNotIn(other_contact.id, ids)

    def test_create_contact_sets_business(self):
        response = self.client.post(
            reverse("api:contact-list"),
            {
                "name": "Vali",
                "phone": "90 111 22 33",
                "address": "Toshkent",
                "type": "customer",
                "note": "Yangi mijoz",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["name"], "Vali")
        self.assertEqual(data["type_display"], "Mijoz")

        from apps.contacts.models import Contact

        contact = Contact.objects.get(pk=data["id"])
        self.assertEqual(contact.business_id, self.business.id)

    def test_create_contact_invalid_type(self):
        response = self.client.post(
            reverse("api:contact-list"),
            {"name": "Vali", "type": "noto-gri"},
            format="json",
        )

        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("type", error["fields"])

    def test_detail_other_tenant_returns_404(self):
        _, _, other_contact = self.create_other_business()

        response = self.client.get(
            reverse("api:contact-detail", args=[other_contact.id])
        )

        self.assert_error(response, code="not_found", status_code=404)

    def test_update_and_delete_contact(self):
        detail_url = reverse("api:contact-detail", args=[self.contact.id])

        response = self.client.patch(
            detail_url, {"name": "Ali Valiyev"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["name"], "Ali Valiyev")

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 204)

        self.assertEqual(
            self.client.get(detail_url).status_code, 404
        )

    def test_delete_contact_with_debts_returns_conflict(self):
        self.make_debt()

        response = self.client.delete(
            reverse("api:contact-detail", args=[self.contact.id])
        )

        error = self.assert_error(
            response, code="contact_has_debts", status_code=409
        )
        self.assertTrue(error["message"])

    def test_search_contacts(self):
        self.client.post(
            reverse("api:contact-list"),
            {"name": "Vali", "phone": "+998909998877"},
            format="json",
        )

        response = self.client.get(
            reverse("api:contact-list"), {"search": "Vali"}
        )

        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Vali")

    def test_summary_keeps_directions_separate_and_returns_strings(self):
        receivable = self.make_debt(amount="1000000.00")
        payable = self.make_debt(
            amount="300000.00", direction="payable"
        )
        add_payment(payable, amount="100000.00", user=self.user)

        response = self.client.get(
            reverse("api:contact-summary", args=[self.contact.id])
        )

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()

        self.assertEqual(data["receivable"]["count"], 1)
        self.assertEqual(data["receivable"]["total_amount"], "1000000.00")
        self.assertEqual(data["receivable"]["remaining"], "1000000.00")
        self.assertEqual(data["payable"]["count"], 1)
        self.assertEqual(data["payable"]["total_amount"], "300000.00")
        self.assertEqual(data["payable"]["paid_total"], "100000.00")
        self.assertEqual(data["payable"]["remaining"], "200000.00")
        self.assertEqual(data["total_count"], 2)

    def test_summary_other_tenant_returns_404(self):
        _, _, other_contact = self.create_other_business()

        response = self.client.get(
            reverse("api:contact-summary", args=[other_contact.id])
        )

        self.assert_error(response, code="not_found", status_code=404)
