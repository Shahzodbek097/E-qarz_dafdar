"""Session autentifikatsiyasi.

DRF'ning standart `SessionAuthentication` klassi autentifikatsiya bo'lmaganda
403 qaytaradi, chunki `WWW-Authenticate` sarlavhasini bilmaydi. API uchun
401 to'g'riroq: frontend "login qilish kerak" holatini shu statusdan ajratadi.
"""

from rest_framework.authentication import (
    SessionAuthentication as DRFSessionAuthentication,
)


class SessionAuthentication(DRFSessionAuthentication):
    def authenticate_header(self, request):
        return "Session"
