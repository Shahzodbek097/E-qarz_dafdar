"""Loyiha darajasidagi kichik yordamchi view'lar."""

from django.http import JsonResponse


def health(request):
    """Server ishlayotganini tekshirish uchun oddiy endpoint.

    Bu endpoint autentifikatsiya talab qilmaydi va hech qanday maxfiy
    ma'lumot qaytarmaydi.
    """
    return JsonResponse({"status": "ok", "service": "E-QarzDaftar"})
