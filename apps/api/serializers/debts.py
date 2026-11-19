"""Qarz serializer'i.

O'qishda hisoblangan maydonlar (`paid_total`, `remaining`, `status`,
`is_overdue`) ham qaytadi. Ular bazada saqlanmaydi — `apps.debts.services`
tomonidan to'lovlar tarixidan hisoblanadi.
"""

from django.utils import timezone
from rest_framework import serializers

from apps.contacts.models import Contact
from apps.debts.models import MIN_MONEY, Debt
from apps.debts.services import get_debt_summary


class DebtSerializer(serializers.ModelSerializer):
    # Mijoz faqat joriy biznesnikilar orasidan tanlanadi.
    contact = serializers.PrimaryKeyRelatedField(
        queryset=Contact.objects.none()
    )
    contact_name = serializers.CharField(source="contact.name", read_only=True)
    direction_display = serializers.CharField(
        source="get_direction_display", read_only=True
    )
    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=MIN_MONEY,
    )

    paid_total = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    days_overdue = serializers.SerializerMethodField()
    # Frontend tahrirlash formasida moliyaviy maydonlarni qulflash uchun.
    has_payments = serializers.SerializerMethodField()

    class Meta:
        model = Debt
        fields = [
            "id",
            "contact",
            "contact_name",
            "direction",
            "direction_display",
            "amount",
            "paid_total",
            "remaining",
            "status",
            "display_status",
            "is_overdue",
            "days_overdue",
            "has_payments",
            "issue_date",
            "due_date",
            "reason",
            "note",
            "is_archived",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_archived", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        business = self.context.get("business")
        if business is not None:
            self.fields["contact"].queryset = Contact.objects.filter(
                business=business
            )

    def _summary(self, obj):
        """Qarz bo'yicha hisob-kitobni bir marta hisoblab, keshlaydi."""
        summary = getattr(obj, "_api_debt_summary", None)
        if summary is None:
            summary = get_debt_summary(obj, today=self.context.get("today"))
            obj._api_debt_summary = summary
        return summary

    def get_paid_total(self, obj):
        return f"{self._summary(obj)['paid_total']:.2f}"

    def get_remaining(self, obj):
        return f"{self._summary(obj)['remaining']:.2f}"

    def get_status(self, obj):
        return self._summary(obj)["status"]

    def get_display_status(self, obj):
        return self._summary(obj)["display_status"]

    def get_is_overdue(self, obj):
        return self._summary(obj)["is_overdue"]

    def get_days_overdue(self, obj):
        return self._summary(obj)["days_overdue"]

    def get_has_payments(self, obj):
        """Qarzda to'lov tarixi bor-yo'qligi.

        View'lar queryset'ni `has_payments` annotation bilan beradi; u bo'lmasa
        (masalan dashboard'dagi 5 ta yozuv) bitta `exists()` so'rovi bajariladi.
        """
        annotated = obj.__dict__.get("has_payments")
        if annotated is None:
            return obj.payments.exists()
        return bool(annotated)

    def validate(self, attrs):
        instance = self.instance

        # To'lov tarixi boshlanganidan keyin moliyaviy maydonlar qulflanadi.
        if instance is not None and instance.payments.exists():
            for field in ("amount", "direction", "contact"):
                if field not in attrs:
                    continue
                if field == "contact":
                    changed = attrs[field].pk != instance.contact_id
                else:
                    changed = attrs[field] != getattr(instance, field)
                if changed:
                    raise serializers.ValidationError(
                        {
                            field: [
                                "To'lovlar mavjud bo'lganda bu maydonni "
                                "o'zgartirish mumkin emas."
                            ]
                        }
                    )

        if instance is None:
            issue_date = attrs.get("issue_date") or timezone.localdate()
            due_date = attrs.get("due_date")
        else:
            issue_date = attrs.get("issue_date", instance.issue_date)
            due_date = attrs.get("due_date", instance.due_date)

        if due_date and issue_date and due_date < issue_date:
            raise serializers.ValidationError(
                {
                    "due_date": [
                        "Qaytarish muddati qarz sanasidan oldin bo'lishi "
                        "mumkin emas."
                    ]
                }
            )

        return attrs
