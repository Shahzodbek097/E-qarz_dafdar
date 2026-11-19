"""Dashboard va hisobot API'si.

Barcha hisob-kitoblar `apps.reports.services` da bajariladi. View faqat
query parametrlarini tekshiradi, servisni chaqiradi va pul qiymatlarini
string ko'rinishida qaytaradi.
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.mixins import BusinessScopedMixin
from apps.api.serializers import (
    DateRangeQuerySerializer,
    DebtSerializer,
    OverdueReportQuerySerializer,
    PaymentSerializer,
    PaymentsReportQuerySerializer,
)
from apps.api.utils import money_to_str
from apps.reports.services import (
    get_dashboard_summary,
    get_debts_report,
    get_overdue_report,
    get_payments_report,
)


class DashboardView(BusinessScopedMixin, APIView):
    def get(self, request):
        business = self.get_business()
        data = get_dashboard_summary(business)
        context = {"request": request, "business": business}

        payload = {
            "totals": data["totals"],
            "recent_debts": DebtSerializer(
                data["recent_debts"], many=True, context=context
            ).data,
            "recent_payments": PaymentSerializer(
                data["recent_payments"], many=True, context=context
            ).data,
            "top_debtors": data["top_debtors"],
        }
        return Response(money_to_str(payload))


class DebtsReportView(BusinessScopedMixin, APIView):
    def get(self, request):
        params = DateRangeQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        data = get_debts_report(
            self.get_business(), **params.validated_data
        )
        return Response(money_to_str(data))


class PaymentsReportView(BusinessScopedMixin, APIView):
    def get(self, request):
        params = PaymentsReportQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        data = get_payments_report(
            self.get_business(), **params.validated_data
        )
        return Response(money_to_str(data))


class OverdueReportView(BusinessScopedMixin, APIView):
    def get(self, request):
        params = OverdueReportQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        data = get_overdue_report(
            self.get_business(), **params.validated_data
        )
        context = {
            "request": request,
            "business": self.get_business(),
            "today": data["as_of"],
        }

        payload = {
            "as_of": data["as_of"],
            "filters": data["filters"],
            "totals": data["totals"],
            "items": DebtSerializer(
                data["items"], many=True, context=context
            ).data,
        }
        return Response(money_to_str(payload))
