from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.accounts.services import normalize_phone, register_user
from apps.businesses.models import Business


class NormalizePhoneTests(TestCase):
    def test_accepts_common_formats(self):
        cases = {
            "+998 90 123 45 67": "+998901234567",
            "998901234567": "+998901234567",
            "90 123 45 67": "+998901234567",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_phone(raw), expected)

    def test_rejects_invalid_format(self):
        with self.assertRaises(ValidationError):
            normalize_phone("12345")


class RegisterUserServiceTests(TestCase):
    def setUp(self):
        self.payload = {
            "username": "ali",
            "password": "KuchliParol123!",
            "first_name": "Ali",
            "last_name": "Valiyev",
            "phone": "+998901234567",
            "email": "ali@example.com",
            "business_name": "Ali Savdo",
            "industry": "retail",
        }

    def _register(self, **overrides):
        data = {**self.payload, **overrides}
        return register_user(**data)

    def test_creates_user_and_business(self):
        user = self._register(
            phone="90 123 45 67",
            email="ALI@EXAMPLE.COM",
        )

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Business.objects.count(), 1)
        self.assertEqual(user.phone, "+998901234567")
        self.assertEqual(user.email, "ali@example.com")
        self.assertTrue(user.check_password("KuchliParol123!"))
        self.assertFalse(user.password == "KuchliParol123!")
        self.assertEqual(user.business.name, "Ali Savdo")
        self.assertEqual(user.business.industry, "retail")
        self.assertEqual(user.business.phone, "+998901234567")

    def test_duplicate_username_rejected(self):
        self._register()
        with self.assertRaises(ValidationError) as ctx:
            self._register(
                username="ALI",
                email="other@example.com",
                phone="+998901112244",
            )
        self.assertIn("username", ctx.exception.message_dict)
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_email_is_case_insensitive(self):
        self._register()
        with self.assertRaises(ValidationError) as ctx:
            self._register(
                username="ali2",
                email="ALI@EXAMPLE.COM",
                phone="+998901112244",
            )
        self.assertIn("email", ctx.exception.message_dict)
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_phone_is_normalized(self):
        self._register()
        with self.assertRaises(ValidationError) as ctx:
            self._register(
                username="ali2",
                email="other@example.com",
                phone="90 123 45 67",
            )
        self.assertIn("phone", ctx.exception.message_dict)
        self.assertEqual(User.objects.count(), 1)

    def test_weak_password_rolls_back_everything(self):
        with self.assertRaises(ValidationError) as ctx:
            self._register(password="123")
        self.assertIn("password", ctx.exception.message_dict)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Business.objects.count(), 0)

    def test_invalid_industry_rolls_back(self):
        with self.assertRaises(ValidationError) as ctx:
            self._register(industry="unknown")
        self.assertIn("industry", ctx.exception.message_dict)
        self.assertEqual(User.objects.count(), 0)

    def test_invalid_phone_rolls_back(self):
        with self.assertRaises(ValidationError) as ctx:
            self._register(phone="12345")
        self.assertIn("phone", ctx.exception.message_dict)
        self.assertEqual(User.objects.count(), 0)

    def test_business_creation_failure_rolls_back_user(self):
        # Biznes yaratishda kutilmagan xato bo'lsa, User ham saqlanmasligi kerak.
        with patch.object(
            Business.objects,
            "create",
            side_effect=RuntimeError("biznes yaratilmadi"),
        ):
            with self.assertRaises(RuntimeError):
                self._register()

        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Business.objects.count(), 0)
