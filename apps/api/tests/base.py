"""API testlari uchun umumiy asos."""

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.testing import (
    create_business_user,
    create_contact,
    create_debt,
)


class ApiTestBase(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.user, self.business = create_business_user()
        self.contact = create_contact(
            self.business,
            name="Ali",
            phone="+998901112233",
        )
        self.client.force_authenticate(self.user)

    def create_other_business(self):
        """Ikkinchi biznes: tenant izolyatsiyasini tekshirish uchun."""
        user, business = create_business_user(
            username="other",
            phone="+998902223344",
            email="other@example.com",
            business_name="Boshqa biznes",
        )
        contact = create_contact(business, name="Boshqa mijoz")
        return user, business, contact

    def make_debt(
        self,
        *,
        contact=None,
        amount="1000000.00",
        direction="receivable",
        issue_date=None,
        due_date=None,
        is_archived=False,
        business=None,
    ):
        return create_debt(
            business or self.business,
            contact or self.contact,
            amount=amount,
            direction=direction,
            issue_date=issue_date or self.today,
            due_date=due_date,
            is_archived=is_archived,
        )

    def assert_error(self, response, *, code, status_code):
        self.assertEqual(
            response.status_code,
            status_code,
            msg=getattr(response, "content", b""),
        )
        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], code)
        self.assertTrue(data["error"]["message"])
        self.assertIsInstance(data["error"]["fields"], dict)
        return data["error"]
