"""View'lar uchun umumiy yordamchilar.

`BusinessScopedMixin` foydalanuvchining biznesini topadi va uni view
ichida keshlaydi. Barcha so'rovlar shu biznes bo'yicha filtrlanadi —
frontend yuborgan `business_id` hech qachon ishonch manbai emas.
"""

from rest_framework.exceptions import NotFound


class BusinessScopedMixin:
    _business = None

    def get_business(self):
        """Joriy foydalanuvchining biznesi yoki 404."""
        if self._business is None:
            business = getattr(self.request.user, "business", None)
            if business is None:
                raise NotFound("Biznes profili topilmadi.")
            self._business = business
        return self._business


class BusinessScopedGenericMixin(BusinessScopedMixin):
    """Generic view'lar uchun: serializer'ga biznesni uzatadi."""

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["business"] = self.get_business()
        return context
