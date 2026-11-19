"""Foydalanuvchilar uchun admin panel sozlamalari."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Standart bo'limlarga telefon raqamini qo'shamiz.
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Qo'shimcha ma'lumotlar", {"fields": ("phone",)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Qo'shimcha ma'lumotlar",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "phone",
                )
            },
        ),
    )

    list_display = (
        "username",
        "first_name",
        "last_name",
        "phone",
        "email",
        "is_staff",
        "date_joined",
    )
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("username", "first_name", "last_name", "phone", "email")
    ordering = ("-date_joined",)
