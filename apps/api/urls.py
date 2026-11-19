"""API v1 URL konfiguratsiyasi.

Barcha manzillar `/api/v1/` prefiksi ostida. Frontend faqat shu API orqali
ishlaydi.
"""

from django.urls import path

from .views import (
    BusinessView,
    ContactDetailView,
    ContactListCreateView,
    ContactSummaryView,
    CsrfView,
    DashboardView,
    DebtArchiveView,
    DebtDetailView,
    DebtListCreateView,
    DebtPaymentListCreateView,
    DebtsReportView,
    LoginView,
    LogoutView,
    MeView,
    MetaView,
    OverdueReportView,
    PaymentDetailView,
    PaymentListView,
    PaymentReverseView,
    PaymentsReportView,
    RegisterView,
)

app_name = "api"

urlpatterns = [
    # Autentifikatsiya
    path("auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("business/", BusinessView.as_view(), name="business"),
    path("meta/", MetaView.as_view(), name="meta"),
    # Mijozlar
    path("contacts/", ContactListCreateView.as_view(), name="contact-list"),
    path(
        "contacts/<int:pk>/",
        ContactDetailView.as_view(),
        name="contact-detail",
    ),
    path(
        "contacts/<int:pk>/summary/",
        ContactSummaryView.as_view(),
        name="contact-summary",
    ),
    # Qarzlar
    path("debts/", DebtListCreateView.as_view(), name="debt-list"),
    path(
        "debts/<int:pk>/",
        DebtDetailView.as_view(),
        name="debt-detail",
    ),
    path(
        "debts/<int:pk>/archive/",
        DebtArchiveView.as_view(archived=True),
        name="debt-archive",
    ),
    path(
        "debts/<int:pk>/unarchive/",
        DebtArchiveView.as_view(archived=False),
        name="debt-unarchive",
    ),
    path(
        "debts/<int:pk>/payments/",
        DebtPaymentListCreateView.as_view(),
        name="debt-payments",
    ),
    # To'lovlar
    path("payments/", PaymentListView.as_view(), name="payment-list"),
    path(
        "payments/<int:pk>/",
        PaymentDetailView.as_view(),
        name="payment-detail",
    ),
    path(
        "payments/<int:pk>/reverse/",
        PaymentReverseView.as_view(),
        name="payment-reverse",
    ),
    # Hisobotlar
    path(
        "reports/dashboard/",
        DashboardView.as_view(),
        name="report-dashboard",
    ),
    path(
        "reports/debts/",
        DebtsReportView.as_view(),
        name="report-debts",
    ),
    path(
        "reports/payments/",
        PaymentsReportView.as_view(),
        name="report-payments",
    ),
    path(
        "reports/overdue/",
        OverdueReportView.as_view(),
        name="report-overdue",
    ),
]
