"""To'lovlar API'si.

To'lov yaratish faqat qarz kontekstida bo'ladi:
`POST /debts/<id>/payments/`. Bu biznes ID'sini URL'dan emas, qarzdan
olishni ta'minlaydi. Bekor qilish alohida endpoint orqali ishlaydi.
"""

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.mixins import BusinessScopedMixin
from apps.api.serializers import (
    PaymentCreateSerializer,
    PaymentListQuerySerializer,
    PaymentSerializer,
    ReversePaymentSerializer,
)
from apps.debts.models import Debt, Payment
from apps.debts.services import add_payment, reverse_payment


class DebtPaymentListCreateView(
    BusinessScopedMixin, generics.ListCreateAPIView
):
    def get_debt(self):
        if not hasattr(self, "_debt"):
            self._debt = get_object_or_404(
                Debt.objects.filter(business=self.get_business()),
                pk=self.kwargs["pk"],
            )
        return self._debt

    def get_queryset(self):
        return (
            Payment.objects.filter(debt=self.get_debt())
            .select_related(
                "debt",
                "debt__contact",
                "created_by",
                "reversed_by",
            )
            .order_by("-payment_date", "-id")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PaymentCreateSerializer
        return PaymentSerializer

    def create(self, request, *args, **kwargs):
        debt = self.get_debt()
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = add_payment(
            debt,
            user=request.user,
            **serializer.validated_data,
        )
        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )


class PaymentListView(BusinessScopedMixin, generics.ListAPIView):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        queryset = Payment.objects.filter(
            debt__business=self.get_business()
        ).select_related(
            "debt",
            "debt__contact",
            "created_by",
            "reversed_by",
        )

        params = PaymentListQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        if data.get("debt"):
            queryset = queryset.filter(debt_id=data["debt"])
        if data.get("method"):
            queryset = queryset.filter(method=data["method"])
        if data.get("is_reversed") is not None:
            queryset = queryset.filter(
                is_reversed=data["is_reversed"] == "true"
            )
        if data.get("date_from"):
            queryset = queryset.filter(
                payment_date__gte=data["date_from"]
            )
        if data.get("date_to"):
            queryset = queryset.filter(payment_date__lte=data["date_to"])

        ordering = data.get("ordering", "-payment_date")
        return queryset.order_by(ordering, "-id")


class PaymentDetailView(BusinessScopedMixin, generics.RetrieveAPIView):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(
            debt__business=self.get_business()
        ).select_related(
            "debt",
            "debt__contact",
            "created_by",
            "reversed_by",
        )


class PaymentReverseView(BusinessScopedMixin, APIView):
    def post(self, request, pk):
        payment = get_object_or_404(
            Payment.objects.filter(debt__business=self.get_business()),
            pk=pk,
        )

        serializer = ReversePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = reverse_payment(
            payment,
            reason=serializer.validated_data["reason"],
            user=request.user,
        )
        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_200_OK,
        )
