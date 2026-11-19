from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.api.tests.base import ApiTestBase
from apps.businesses.models import Business


class AuthApiTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        # Auth testlarida haqiqiy session oqimini tekshiramiz.
        self.client.force_authenticate(None)

    def register_payload(self, **overrides):
        payload = {
            "username": "yangi",
            "password": "KuchliParol123!",
            "password_confirm": "KuchliParol123!",
            "first_name": "Yangi",
            "last_name": "Foydalanuvchi",
            "phone": "+998907778899",
            "email": "yangi@example.com",
            "business_name": "Yangi biznes",
            "industry": "retail",
        }
        payload.update(overrides)
        return payload

    def login(self, username="owner", password="TestParol123!"):
        return self.client.post(
            reverse("api:auth-login"),
            {"username": username, "password": password},
            format="json",
        )

    def test_csrf_endpoint_sets_cookie(self):
        response = self.client.get(reverse("api:auth-csrf"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrfToken", response.json())
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)

    def test_register_creates_user_and_business_without_login(self):
        response = self.client.post(
            reverse("api:auth-register"),
            self.register_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["user"]["username"], "yangi")
        self.assertEqual(data["user"]["phone"], "+998907778899")
        self.assertEqual(data["business"]["name"], "Yangi biznes")
        self.assertEqual(data["business"]["industry"], "retail")
        self.assertTrue(User.objects.filter(username="yangi").exists())
        self.assertTrue(
            Business.objects.filter(name="Yangi biznes").exists()
        )

        # Ro'yxatdan o'tish avtomatik login qilmaydi.
        me = self.client.get(reverse("api:auth-me"))
        self.assert_error(
            me, code="not_authenticated", status_code=401
        )

    def test_register_duplicate_username_returns_fields(self):
        response = self.client.post(
            reverse("api:auth-register"),
            self.register_payload(username="owner"),
            format="json",
        )

        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("username", error["fields"])

    def test_register_password_mismatch(self):
        response = self.client.post(
            reverse("api:auth-register"),
            self.register_payload(password_confirm="BoshqaParol123!"),
            format="json",
        )

        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("password_confirm", error["fields"])

    def test_register_invalid_phone(self):
        response = self.client.post(
            reverse("api:auth-register"),
            self.register_payload(phone="12345"),
            format="json",
        )

        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("phone", error["fields"])

    def test_register_weak_password_returns_field_error(self):
        response = self.client.post(
            reverse("api:auth-register"),
            self.register_payload(
                password="12345678",
                password_confirm="12345678",
            ),
            format="json",
        )

        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("password", error["fields"])

    def test_login_success_and_session_auth(self):
        response = self.login()

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["user"]["username"], "owner")
        self.assertEqual(
            response.json()["business"]["name"], "Test biznes"
        )

        me = self.client.get(reverse("api:auth-me"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["username"], "owner")

    def test_login_wrong_password(self):
        response = self.login(password="Noto'g'riParol123!")

        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("non_field_errors", error["fields"])

    def test_logout_ends_session(self):
        self.assertEqual(self.login().status_code, 200)

        response = self.client.post(reverse("api:auth-logout"))
        self.assertEqual(response.status_code, 204)

        me = self.client.get(reverse("api:auth-me"))
        self.assert_error(
            me, code="not_authenticated", status_code=401
        )

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("api:auth-me"))
        self.assert_error(
            response, code="not_authenticated", status_code=401
        )

    def test_me_returns_user_and_business(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("api:auth-me"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user"]["id"], self.user.id)
        self.assertEqual(data["user"]["full_name"], "Test Foydalanuvchi")
        self.assertEqual(data["business"]["id"], self.business.id)

    def test_patch_me_normalizes_phone(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            reverse("api:auth-me"),
            {"phone": "90 123 45 67", "first_name": "Ali"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "+998901234567")
        self.assertEqual(self.user.first_name, "Ali")

    def test_patch_me_rejects_duplicate_email_case_insensitive(self):
        User.objects.create_user(
            username="boshqa",
            password="TestParol123!",
            first_name="Boshqa",
            last_name="Foydalanuvchi",
            phone="+998905556677",
            email="band@example.com",
        )
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            reverse("api:auth-me"),
            {"email": "BAND@example.com"},
            format="json",
        )

        error = self.assert_error(
            response, code="validation_error", status_code=400
        )
        self.assertIn("email", error["fields"])

    def test_business_patch_updates_profile(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            reverse("api:business"),
            {
                "name": "Yangi nom",
                "industry": "services",
                "phone": "90 123 45 67",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, "Yangi nom")
        self.assertEqual(self.business.industry, "services")
        self.assertEqual(self.business.phone, "+998901234567")

    def test_login_requires_csrf_when_enforced(self):
        client = APIClient(enforce_csrf_checks=True)
        payload = {"username": "owner", "password": "TestParol123!"}

        # Token yo'q — 403.
        response = client.post(
            reverse("api:auth-login"), payload, format="json"
        )
        self.assertEqual(response.status_code, 403)

        # Token bilan — 200.
        token = client.get(reverse("api:auth-csrf")).json()["csrfToken"]
        response = client.post(
            reverse("api:auth-login"),
            payload,
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200, response.content)
