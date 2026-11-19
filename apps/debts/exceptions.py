"""Qarz biznes qoidalari buzilganda ko'tariladigan xatoliklar.

Bu xatoliklar HTTP'dan mustaqil: ularni API qatlami (3-bosqich) tegishli
HTTP status va yagona JSON formatiga aylantiradi.
"""


class DebtError(Exception):
    """Barcha qarz xatoliklari uchun asosiy sinf."""

    code = "debt_error"

    def __init__(self, message, *, code=None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class InvalidPaymentAmountError(DebtError):
    code = "invalid_payment_amount"


class InvalidPaymentMethodError(DebtError):
    code = "invalid_payment_method"


class OverpaymentError(DebtError):
    """To'lov qolgan qarzdan katta bo'lganda ko'tariladi."""

    code = "overpayment"

    def __init__(self, remaining):
        self.remaining = remaining
        if remaining <= 0:
            message = "Qarz allaqachon to'liq to'langan."
        else:
            message = (
                "To'lov qolgan qarzdan oshib ketdi. "
                f"Qolgan qarz: {remaining}"
            )
        super().__init__(message)


class PaymentAlreadyReversedError(DebtError):
    code = "payment_already_reversed"


class ReversalReasonRequiredError(DebtError):
    code = "reversal_reason_required"


class DebtHasPaymentsError(DebtError):
    code = "debt_has_payments"
