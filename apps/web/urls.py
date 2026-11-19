"""Frontend URL konfiguratsiyasi."""

from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.index, name="index"),
    path("assets/<path:path>", views.asset, name="asset"),
]
