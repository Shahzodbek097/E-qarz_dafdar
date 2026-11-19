"""Pul qiymatlarini API javobida string ko'rinishiga keltirish.

DRF'ning `DecimalField` maydoni pulni string qilib qaytaradi. Lekin hisobot
va jamlanma javoblari oddiy dict bo'lgani uchun ular ichidagi `Decimal`
qiymatlarni ham bir xil formatga keltirish kerak: `"1000000.00"`.
Bu frontendda float xatoliklarining oldini oladi.
"""

from decimal import Decimal


def money_to_str(value):
    """Dict/list ichidagi barcha Decimal qiymatlarni stringga aylantiradi."""
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, dict):
        return {key: money_to_str(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [money_to_str(item) for item in value]
    return value
