"""Mijoz / hamkor turlari."""

from django.db import models


class ContactType(models.TextChoices):
    CUSTOMER = "customer", "Mijoz"
    SUPPLIER = "supplier", "Ta'minotchi"
    OTHER = "other", "Boshqa"
