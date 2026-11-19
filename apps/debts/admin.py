"""Qarz va to'lovlar uchun admin panel.

Muhim: to'lovlar admin orqali qo'shilmaydi, tahrirlanmaydi va o'chirilmaydi.
Ular faqat API/service qatlami orqali kiritiladi. Sabab: qoldiqni tekshirish,
atomar tranzaksiya va audit qoidalari service ichida bajariladi.
"""

from django.contrib import admin

from .models import Debt, Payment


class PaymentInline(admin.TabularInline):
    """Qarz sahifasida to'lovlarni faqat o'qish uchun ko'rsatadi."""

    model = Payment
    extra = 0
    can_delete = False
    readonly_fields = (
        "amount",
        "payment_date",
        "method",
        "note",
        "is_reversed",
        "reversed_at",
        "reversal_reason",
        "created_by",
        "created_at",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "contact",
        "business",
        "direction",
        "amount",
        "issue_date",
        "due_date",
        "is_archived",
    )
    list_filter = ("direction", "is_archived", "business")
    search_fields = ("contact__name", "contact__phone", "reason", "business__name")
    readonly_fields = ("created_at", "updated_at")
    inlines = [PaymentInline]

    def get_readonly_fields(self, request, obj=None):
        """To'lovi bor qarzning moliyaviy maydonlarini qulflaydi.

        Bu admin orqali ham to'lovlar tarixiga zid o'zgartirish kiritilishining
        oldini oladi.
        """
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.payments.exists():
            readonly += ["business", "contact", "direction", "amount"]
        return readonly


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """To'lovlar tarixi — faqat ko'rish uchun."""

    list_display = (
        "id",
        "debt",
        "amount",
        "payment_date",
        "method",
        "is_reversed",
        "created_at",
    )
    list_filter = ("method", "is_reversed")
    search_fields = ("debt__contact__name", "debt__business__name")
    readonly_fields = (
        "debt",
        "amount",
        "payment_date",
        "method",
        "note",
        "created_by",
        "created_at",
        "is_reversed",
        "reversed_at",
        "reversal_reason",
        "reversed_by",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
