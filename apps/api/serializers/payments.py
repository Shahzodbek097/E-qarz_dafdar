"""To'lov serializer'lari."""

from rest_framework import serializers

from apps.debts.choices import PaymentMethod
from apps.debts.models import MIN_MONEY, Payment


class PaymentSerializer(serializers.ModelSerializer):
    debt_contact_name = serializers.CharField(
        source="debt.contact.name", read_only=True
    )
    method_display = serializers.CharField(
        source="get_method_display", read_only=True
    )
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    created_by = serializers.SerializerMethodField()
    reversed_by = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "debt",
            "debt_contact_name",
            "amount",
            "payment_date",
            "method",
            "method_display",
            "note",
            "is_reversed",
            "reversed_at",
            "reversal_reason",
            "created_by",
            "reversed_by",
            "created_at",
        ]
        read_only_fields = fields

    def get_created_by(self, obj):
        return obj.created_by.username if obj.created_by_id else None

    def get_reversed_by(self, obj):
        return obj.reversed_by.username if obj.reversed_by_id else None


class PaymentCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=MIN_MONEY,
    )
    payment_date = serializers.DateField(required=False)
    method = serializers.ChoiceField(
        choices=PaymentMethod.choices,
        required=False,
        default=PaymentMethod.CASH,
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class ReversePaymentSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False, trim_whitespace=True)
