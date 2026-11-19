"""Testlar uchun ma'lumot yaratuvchi yordamchilar.

Bu modul faqat testlarda ishlatiladi; production kodda import qilinmaydi.
Har bir funksiya bazaga yozuv yaratadi.
"""

from datetime import date
from decimal import Decimal

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.contacts.models import Contact
from apps.debts.choices import DebtDirection
from apps.debts.models import Debt


def create_business_user(
    *,
    username="owner",
    phone="+998901112233",
    email="owner@example.com",
    business_name="Test biznes",
    industry="retail",
):
    """Foydalanuvchi + biznes yaratadi va ikkalasini qaytaradi."""
    user = User.objects.create_user(
        username=username,
        password="TestParol123!",
        first_name="Test",
        last_name="Foydalanuvchi",
        phone=phone,
        email=email,
    )
    business = Business.objects.create(
        owner=user,
        name=business_name,
        industry=industry,
        phone=phone,
    )
    return user, business


def create_contact(business, *, name="Mijoz", phone="", type="customer"):
    return Contact.objects.create(
        business=business,
        name=name,
        phone=phone,
        type=type,
    )


def create_debt(
    business,
    contact,
    *,
    amount="1000000.00",
    direction=DebtDirection.RECEIVABLE,
    issue_date=date(2026, 1, 1),
    due_date=None,
    reason="test",
    is_archived=False,
    created_by=None,
):
    return Debt.objects.create(
        business=business,
        contact=contact,
        direction=direction,
        amount=Decimal(str(amount)),
        issue_date=issue_date,
        due_date=due_date,
        reason=reason,
        is_archived=is_archived,
        created_by=created_by,
    )
