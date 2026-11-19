"""Query parametrlarini tekshiruvchi serializer'lar.

Ro'yxat va hisobot endpointlari query parametrlarini shu serializer'lar
orqali o'qiydi. Noto'g'ri qiymat yuborilsa, DRF `ValidationError` ko'tariladi
va u yagona xatolik formatiga aylanadi.
"""

from rest_framework import serializers

from apps.contacts.choices import ContactType
from apps.debts.choices import DebtDirection, DebtStatus, PaymentMethod


class ContactListQuerySerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True)
    type = serializers.ChoiceField(choices=ContactType.choices, required=False)
    ordering = serializers.ChoiceField(
        choices=[
            "name",
            "-name",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
        ],
        required=False,
    )


class DebtListQuerySerializer(serializers.Serializer):
    archived = serializers.ChoiceField(
        choices=["true", "false", "all"],
        required=False,
        default="false",
    )
    direction = serializers.ChoiceField(
        choices=DebtDirection.choices, required=False
    )
    status = serializers.ChoiceField(
        choices=DebtStatus.choices, required=False
    )
    contact = serializers.IntegerField(required=False, min_value=1)
    search = serializers.CharField(required=False, allow_blank=True)
    ordering = serializers.ChoiceField(
        choices=[
            "created_at",
            "-created_at",
            "issue_date",
            "-issue_date",
            "due_date",
            "-due_date",
            "amount",
            "-amount",
            "id",
            "-id",
        ],
        required=False,
    )


class PaymentListQuerySerializer(serializers.Serializer):
    debt = serializers.IntegerField(required=False, min_value=1)
    method = serializers.ChoiceField(
        choices=PaymentMethod.choices, required=False
    )
    is_reversed = serializers.ChoiceField(
        choices=["true", "false"], required=False
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    ordering = serializers.ChoiceField(
        choices=[
            "payment_date",
            "-payment_date",
            "created_at",
            "-created_at",
            "amount",
            "-amount",
        ],
        required=False,
    )

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                {
                    "date_to": [
                        "Sana oralig'i noto'g'ri: boshlanish sanasi "
                        "tugash sanasidan katta bo'lishi mumkin emas."
                    ]
                }
            )
        return attrs


class DateRangeQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    group_by = serializers.ChoiceField(
        choices=["day", "month"], required=False, default="day"
    )
    direction = serializers.ChoiceField(
        choices=DebtDirection.choices, required=False
    )

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                {
                    "date_to": [
                        "Sana oralig'i noto'g'ri: boshlanish sanasi "
                        "tugash sanasidan katta bo'lishi mumkin emas."
                    ]
                }
            )
        return attrs


class PaymentsReportQuerySerializer(DateRangeQuerySerializer):
    method = serializers.ChoiceField(
        choices=PaymentMethod.choices, required=False
    )


class OverdueReportQuerySerializer(serializers.Serializer):
    as_of = serializers.DateField(required=False)
    direction = serializers.ChoiceField(
        choices=DebtDirection.choices, required=False
    )
