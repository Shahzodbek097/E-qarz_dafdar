"""
E-QarzDaftar — Django sozlamalari.

Bu fayl loyihaning umumiy konfiguratsiyasini saqlaydi:
- o'rnatilgan ilovalar;
- ma'lumotlar bazasi (SQLite);
- autentifikatsiya va CSRF;
- REST API (DRF) sozlamalari;
- til va vaqt zonasi.

Maxfiy qiymatlar (SECRET_KEY, DEBUG, ALLOWED_HOSTS) muhit o'zgaruvchilari
orqali beriladi. Local ishlash uchun xavfsiz bo'lmagan default qiymatlar bor.
"""

import os
from pathlib import Path

# Loyiha ildiz papkasi: D:\NewProject\E-qarz_dafdar
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Xavfsizlik va debug
# ---------------------------------------------------------------------------

# Production'da DJANGO_SECRET_KEY muhit o'zgaruvchisi albatta berilishi kerak.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-e-qarzdaftar-change-me",
)

# DJANGO_DEBUG=0 bo'lsa debug o'chadi.
DEBUG = os.environ.get("DJANGO_DEBUG", "1").lower() in {"1", "true", "yes"}

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
    ).split(",")
    if host.strip()
]


# ---------------------------------------------------------------------------
# Ilovalar
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Uchinchi tomon
    "rest_framework",

    # Loyiha ilovalari
    "apps.accounts",
    "apps.businesses",
    "apps.contacts",
    "apps.debts",
    "apps.reports",
    "apps.api",
    "apps.web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ---------------------------------------------------------------------------
# Ma'lumotlar bazasi
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ---------------------------------------------------------------------------
# Autentifikatsiya
# ---------------------------------------------------------------------------

# Custom User modeli. Bu qiymat birinchi migratsiyadan oldin belgilanishi shart.
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# ---------------------------------------------------------------------------
# Til va vaqt
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Statik fayllar
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    # Faqat session autentifikatsiyasi: cookie + CSRF.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.api.authentication.SessionAuthentication",
    ],
    # Default holatda barcha API endpointlar himoyalangan.
    # Ochiq endpointlar (register/login/csrf) view ichida alohida belgilanadi.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.api.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    # Yagona xatolik formati: {"error": {"code", "message", "fields"}}
    "EXCEPTION_HANDLER": "apps.api.exceptions.api_exception_handler",
    # Pul qiymatlari har doim string bo'lib qaytadi: "1000000.00"
    "COERCE_DECIMAL_TO_STRING": True,
    "DATE_FORMAT": "%Y-%m-%d",
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
}

# DEBUG rejimida DRF'ning brauzer interfeysi ham ochiladi.
if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ]
else:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer",
    ]


# ---------------------------------------------------------------------------
# CSRF va session cookie
# ---------------------------------------------------------------------------

# Frontend CSRF tokenini JavaScript orqali o'qishi kerak.
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


# ---------------------------------------------------------------------------
# Boshqa
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
