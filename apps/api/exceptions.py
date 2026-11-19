"""API uchun yagona xatolik formati.

Barcha xatoliklar bir xil ko'rinishda qaytadi:

    {
        "error": {
            "code": "validation_error",
            "message": "Kiritilgan ma'lumotlarda xatolik bor.",
            "fields": {"amount": ["To'lov summasi noto'g'ri."]}
        }
    }

Frontend shu formatga tayanadi: `code` bo'yicha xatti-harakat tanlaydi,
`fields` bo'yicha input ostida xabar ko'rsatadi.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.deletion import ProtectedError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.debts.exceptions import DebtError

# Biznes xatoliklarining HTTP statuslari. 400 — so'rov noto'g'ri,
# 409 — joriy holat bilan ziddiyat (masalan, ortiqcha to'lov).
DEBT_ERROR_STATUS = {
    "invalid_payment_amount": status.HTTP_400_BAD_REQUEST,
    "invalid_payment_method": status.HTTP_400_BAD_REQUEST,
    "reversal_reason_required": status.HTTP_400_BAD_REQUEST,
    "overpayment": status.HTTP_409_CONFLICT,
    "payment_already_reversed": status.HTTP_409_CONFLICT,
    "debt_has_payments": status.HTTP_409_CONFLICT,
}


class ConflictError(exceptions.APIException):
    """Joriy holat bilan ziddiyat: 409."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Amalni bajarish mumkin emas."
    default_code = "conflict"


def _flatten(value):
    """DRF/Django xatolik strukturasini faqat dict/list/str ga keltiradi."""
    if isinstance(value, dict):
        return {str(key): _flatten(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_flatten(item) for item in value]
    return str(value)


def _first_message(value):
    """Strukturadan birinchi mazmunli xabarni oladi."""
    if isinstance(value, dict):
        for item in value.values():
            message = _first_message(item)
            if message:
                return message
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            message = _first_message(item)
            if message:
                return message
        return None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def error_response(code, message, *, status_code, fields=None):
    """Yagona xatolik javobini yaratadi."""
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "fields": fields or {},
            }
        },
        status=status_code,
    )


def api_exception_handler(exc, context):
    """DRF'ning standart handler'ini yagona formatga o'raydi."""
    # 1. Biznes qatlami xatoliklari (qarz/to'lov).
    if isinstance(exc, DebtError):
        status_code = DEBT_ERROR_STATUS.get(
            exc.code, status.HTTP_400_BAD_REQUEST
        )
        return error_response(exc.code, str(exc), status_code=status_code)

    # 2. Biznesga tegishli bo'lmagan resursga ruxsat.
    if isinstance(exc, PermissionError):
        return error_response(
            "permission_denied",
            str(exc) or "Bu amal uchun ruxsat yo'q.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # 3. Service qatlamidagi Django ValidationError.
    if isinstance(exc, DjangoValidationError):
        fields = _flatten(
            getattr(exc, "message_dict", {"non_field_errors": exc.messages})
        )
        return error_response(
            "validation_error",
            _first_message(fields) or "Kiritilgan ma'lumotlarda xatolik bor.",
            status_code=status.HTTP_400_BAD_REQUEST,
            fields=fields,
        )

    # 4. Topilmadi.
    if isinstance(exc, Http404):
        return error_response(
            "not_found",
            "So'ralgan resurs topilmadi.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # 5. PROTECT bog'lanishi tufayli o'chirib bo'lmadi.
    if isinstance(exc, ProtectedError):
        return error_response(
            "protected",
            "Bu yozuvga bog'langan ma'lumotlar bor, uni o'chirish mumkin emas.",
            status_code=status.HTTP_409_CONFLICT,
        )

    # 6. DRF'ning o'z xatoliklari.
    response = drf_exception_handler(exc, context)
    if response is None:
        # Noma'lum xato: Django'ning 500 handler'i ishlaydi.
        return None

    if isinstance(exc, exceptions.ValidationError):
        fields = _flatten(response.data)
        return error_response(
            "validation_error",
            _first_message(fields) or "Kiritilgan ma'lumotlarda xatolik bor.",
            status_code=response.status_code,
            fields=fields,
        )

    code = getattr(exc, "default_code", "error")
    if isinstance(exc, exceptions.APIException):
        # `ConflictError(..., code="contact_has_debts")` kabi holatlarda
        # kod `default_code` da emas, `detail` ichida saqlanadi.
        codes = exc.get_codes()
        if isinstance(codes, str):
            code = codes
    message = _first_message(response.data) or "Xatolik yuz berdi."

    if isinstance(exc, exceptions.NotAuthenticated):
        code = "not_authenticated"
        message = "Avtorizatsiya talab qilinadi."
    elif isinstance(exc, exceptions.AuthenticationFailed):
        code = "authentication_failed"
    elif isinstance(exc, exceptions.PermissionDenied):
        code = "permission_denied"
    elif isinstance(exc, exceptions.NotFound):
        code = "not_found"
        message = "So'ralgan resurs topilmadi."
    elif isinstance(exc, exceptions.MethodNotAllowed):
        code = "method_not_allowed"
        message = (
            "Bu HTTP metodi ushbu endpoint uchun ruxsat etilmagan."
        )
    elif isinstance(exc, exceptions.UnsupportedMediaType):
        code = "unsupported_media_type"
        message = "So'rov formati qo'llab-quvvatlanmaydi."
    elif isinstance(exc, exceptions.Throttled):
        code = "throttled"
        message = "So'rovlar soni chegaradan oshdi."
    elif isinstance(exc, exceptions.ParseError):
        code = "parse_error"
        message = "So'rov tanasi noto'g'ri JSON."

    return error_response(code, message, status_code=response.status_code)
