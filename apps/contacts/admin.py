"""Mijozlar uchun admin panel."""

from django.contrib import admin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "business", "type", "phone", "created_at")
    list_filter = ("type", "business")
    search_fields = ("name", "phone", "business__name")
    readonly_fields = ("created_at", "updated_at")
