from django.urls import reverse

from apps.api.tests.base import ApiTestBase


class SecurityApiTests(ApiTestBase):
    def test_private_endpoints_require_authentication(self):
        self.client.force_authenticate(None)

        for url in (
            reverse("api:contact-list"),
            reverse("api:debt-list"),
            reverse("api:payment-list"),
            reverse("api:report-dashboard"),
            reverse("api:report-debts"),
            reverse("api:report-payments"),
            reverse("api:report-overdue"),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assert_error(
                    response,
                    code="not_authenticated",
                    status_code=401,
                )

    def test_method_not_allowed_uses_unified_error(self):
        response = self.client.put(reverse("api:payment-list"))

        self.assert_error(
            response, code="method_not_allowed", status_code=405
        )

    def test_meta_returns_all_choices(self):
        response = self.client.get(reverse("api:meta"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        for key in (
            "debt_directions",
            "debt_statuses",
            "payment_methods",
            "contact_types",
            "industries",
        ):
            with self.subTest(key=key):
                self.assertTrue(data[key])
                self.assertIn("value", data[key][0])
                self.assertIn("label", data[key][0])

    def test_unknown_resource_returns_unified_404(self):
        response = self.client.get(
            reverse("api:debt-detail", args=[999999])
        )

        self.assert_error(response, code="not_found", status_code=404)
