"""Mijoz serializer'i."""

from rest_framework import serializers

from apps.contacts.models import Contact


class ContactSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(
        source="get_type_display", read_only=True
    )

    class Meta:
        model = Contact
        fields = [
            "id",
            "name",
            "phone",
            "address",
            "type",
            "type_display",
            "note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("Mijoz nomi majburiy.")
        return name
