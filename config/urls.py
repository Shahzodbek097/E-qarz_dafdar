"""Loyihaning asosiy URL konfiguratsiyasi.

- `admin/` — Django admin panel;
- `health/` — oddiy health check;
- `api/v1/` — REST API (frontend faqat shu yerga murojaat qiladi).
"""

from django.contrib import admin
from django.urls import include, path

from config.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/v1/", include("apps.api.urls")),
    # Frontend eng oxirida: aniqroq manzillar yuqorida turadi.
    path("", include("apps.web.urls")),
]
