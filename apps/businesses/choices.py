"""Biznes faoliyati sohalari.

`TextChoices` — Django'ning standart yordamchisi. Bazada qisqa kod
(masalan "retail") saqlanadi, foydalanuvchiga esa o'zbekcha nom ko'rsatiladi.
"""

from django.db import models


class Industry(models.TextChoices):
    RETAIL = "retail", "Chakana savdo"
    CLOTHING = "clothing", "Kiyim-kechak"
    FOOD = "food", "Oziq-ovqat"
    SERVICES = "services", "Xizmat ko'rsatish"
    AUTO_SERVICE = "auto_service", "Avtoservis / ustaxona"
    CONSTRUCTION = "construction", "Qurilish materiallari"
    EDUCATION = "education", "O'quv markazi"
    OTHER = "other", "Boshqa"
