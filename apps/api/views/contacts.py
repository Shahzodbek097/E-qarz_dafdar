"""Mijozlar API'si."""

from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.exceptions import ConflictError
from apps.api.mixins import BusinessScopedGenericMixin, BusinessScopedMixin
from apps.api.serializers import ContactListQuerySerializer, ContactSerializer
from apps.api.utils import money_to_str
from apps.contacts.models import Contact
from apps.debts.services import get_contact_debt_summary


class ContactListCreateView(
    BusinessScopedGenericMixin, generics.ListCreateAPIView
):
    serializer_class = ContactSerializer

    def get_queryset(self):
        queryset = Contact.objects.filter(business=self.get_business())

        params = ContactListQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        search = (data.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(phone__icontains=search)
            )
        if data.get("type"):
            queryset = queryset.filter(type=data["type"])
        if data.get("ordering"):
            queryset = queryset.order_by(data["ordering"], "id")
        return queryset

    def perform_create(self, serializer):
        serializer.save(business=self.get_business())


class ContactDetailView(
    BusinessScopedGenericMixin, generics.RetrieveUpdateDestroyAPIView
):
    serializer_class = ContactSerializer

    def get_queryset(self):
        return Contact.objects.filter(business=self.get_business())

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ConflictError(
                "Qarzlari bor mijozni o'chirish mumkin emas. "
                "Avval qarzlarni o'chiring yoki arxivlang.",
                code="contact_has_debts",
            )


class ContactSummaryView(BusinessScopedMixin, APIView):
    def get(self, request, pk):
        contact = get_object_or_404(
            Contact.objects.filter(business=self.get_business()),
            pk=pk,
        )
        include_archived = request.query_params.get(
            "include_archived", ""
        ).lower() in {"1", "true", "yes"}

        summary = get_contact_debt_summary(
            contact, include_archived=include_archived
        )
        return Response(money_to_str(summary), status=status.HTTP_200_OK)
