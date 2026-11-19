"""Frontend uchun tanlovlar (choices) ma'lumoti.

Frontend select'larni to'ldirish uchun qiymat va o'zbekcha nomni oladi.
Bu ma'lumot kodda takrorlanmasligi uchun backenddagi `TextChoices` dan
olinadi.
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.businesses.choices import Industry
from apps.contacts.choices import ContactType
from apps.debts.choices import DebtDirection, DebtStatus, PaymentMethod


def _choices(enum):
    return [
        {"value": value, "label": label} for value, label in enum.choices
    ]


class MetaView(APIView):
    def get(self, request):
        return Response(
            {
                "debt_directions": _choices(DebtDirection),
                "debt_statuses": _choices(DebtStatus),
                "payment_methods": _choices(PaymentMethod),
                "contact_types": _choices(ContactType),
                "industries": _choices(Industry),
            }
        )
