from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """20 elementos por defecto; el cliente puede pedir hasta 100 con ?page_size=."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
