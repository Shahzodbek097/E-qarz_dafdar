"""Biznes profili uchun admin panel."""

from django.contrib import admin

from .models import Business


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "industry", "owner", "phone", "created_at")
    list_filter = ("industry",)
    search_fields = ("name", "phone", "owner__username", "owner__phone")
    readonly_fields = ("created_at", "updated_at")
