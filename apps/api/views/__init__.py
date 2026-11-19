"""API view'lari."""

from .auth import (
    BusinessView,
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
)
from .contacts import (
    ContactDetailView,
    ContactListCreateView,
    ContactSummaryView,
)
from .debts import DebtArchiveView, DebtDetailView, DebtListCreateView
from .meta import MetaView
from .payments import (
    DebtPaymentListCreateView,
    PaymentDetailView,
    PaymentListView,
    PaymentReverseView,
)
from .reports import (
    DashboardView,
    DebtsReportView,
    OverdueReportView,
    PaymentsReportView,
)

__all__ = [
    "BusinessView",
    "ContactDetailView",
    "ContactListCreateView",
    "ContactSummaryView",
    "CsrfView",
    "DashboardView",
    "DebtArchiveView",
    "DebtDetailView",
    "DebtListCreateView",
    "DebtPaymentListCreateView",
    "DebtsReportView",
    "LoginView",
    "LogoutView",
    "MeView",
    "MetaView",
    "OverdueReportView",
    "PaymentDetailView",
    "PaymentListView",
    "PaymentReverseView",
    "PaymentsReportView",
    "RegisterView",
]
