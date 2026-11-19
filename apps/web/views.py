"""Frontend fayllarini same-origin tarzda uzatuvchi view'lar.

Frontend alohida `frontend/` papkasida turadi va faqat `/api/v1/` orqali
backend bilan gaplashadi. Bu view faqat ruxsat etilgan papka ichidagi
fayllarni qaytaradi: `../` orqali loyiha fayllarini o'qish mumkin emas.
"""

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET

FRONTEND_DIR = (settings.BASE_DIR / "frontend").resolve()

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}


def _serve_file(path: Path) -> FileResponse:
    content_type = CONTENT_TYPES.get(path.suffix.lower())
    if content_type is None:
        content_type = mimetypes.guess_type(str(path))[0] or (
            "application/octet-stream"
        )

    response = FileResponse(open(path, "rb"), content_type=content_type)
    response["Cache-Control"] = (
        "no-cache" if settings.DEBUG else "public, max-age=3600"
    )
    return response


@require_GET
def index(request):
    return _serve_file(FRONTEND_DIR / "index.html")


@require_GET
def asset(request, path):
    target = (FRONTEND_DIR / path).resolve()

    # Whitelist: fayl faqat `frontend/` ichida bo'lishi shart.
    try:
        target.relative_to(FRONTEND_DIR)
    except ValueError:
        raise Http404("Fayl topilmadi.")

    if not target.is_file():
        raise Http404("Fayl topilmadi.")

    return _serve_file(target)
