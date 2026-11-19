"""API uchun standart sahifalash.

Frontend `?page=2&page_size=50` bilan sahifalaydi. `page_size` chegarasi
100 ta: juda katta so'rov bilan bazani yuklamaslik uchun.
"""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
