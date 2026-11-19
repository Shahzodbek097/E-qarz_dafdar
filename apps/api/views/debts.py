"""Qarzlar API'si."""

from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.mixins import BusinessScopedGenericMixin, BusinessScopedMixin
from apps.api.serializers import DebtListQuerySerializer, DebtSerializer
from apps.debts.models import Debt, Payment
from apps.debts.services import (
    annotate_debt_totals,
    archive_debt,
    delete_debt,
    filter_debts_by_status,
)


def with_payment_flag(queryset):
    """Har bir qarzga `has_payments` bayrog'ini qo'shadi.

    `Exists` ishlatiladi: JOIN hosil qilmaydi, shuning uchun `remaining` kabi
    Subquery annotatsiyalari va `.values()` bilan guruhlashga ta'sir qilmaydi.
    """
    return queryset.annotate(
        has_payments=Exists(
            Payment.objects.filter(debt=OuterRef("pk"))
        )
    )


class DebtListCreateView(
    BusinessScopedGenericMixin, generics.ListCreateAPIView
):
    serializer_class = DebtSerializer

    def get_queryset(self):
        queryset = Debt.objects.filter(business=self.get_business())

        params = DebtListQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        archived = data["archived"]
        if archived == "false":
            queryset = queryset.filter(is_archived=False)
        elif archived == "true":
            queryset = queryset.filter(is_archived=True)

        queryset = annotate_debt_totals(queryset)
        queryset = with_payment_flag(queryset)

        if data.get("direction"):
            queryset = queryset.filter(direction=data["direction"])
        if data.get("contact"):
            queryset = queryset.filter(contact_id=data["contact"])

        search = (data.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(contact__name__icontains=search)
                | Q(reason__icontains=search)
                | Q(note__icontains=search)
            )

        if data.get("status"):
            queryset = filter_debts_by_status(queryset, data["status"])

        if data.get("ordering"):
            queryset = queryset.order_by(data["ordering"], "-id")

        return queryset

    def perform_create(self, serializer):
        serializer.save(
            business=self.get_business(),
            created_by=self.request.user,
        )


class DebtDetailView(
    BusinessScopedGenericMixin, generics.RetrieveUpdateDestroyAPIView
):
    serializer_class = DebtSerializer

    def get_queryset(self):
        return with_payment_flag(
            annotate_debt_totals(
                Debt.objects.filter(business=self.get_business())
            )
        )

    def perform_destroy(self, instance):
        # To'lovi bor qarz `DebtHasPaymentsError` beradi (409).
        delete_debt(instance)


class DebtArchiveView(BusinessScopedMixin, APIView):
    """Qarzni arxivlash yoki arxivdan qaytarish.

    URL'da `as_view(archived=True/False)` orqali ikki xil ishlatiladi.
    """

    archived = True

    def post(self, request, pk):
        debt = get_object_or_404(
            Debt.objects.filter(business=self.get_business()),
            pk=pk,
        )
        archive_debt(debt, archived=self.archived)

        debt = with_payment_flag(
            annotate_debt_totals(Debt.objects.filter(pk=debt.pk))
        ).get()
        serializer = DebtSerializer(
            debt,
            context={
                "request": request,
                "business": self.get_business(),
            },
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
