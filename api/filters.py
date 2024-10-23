import datetime
from django_filters import rest_framework as filters
from django.db.models import Q

from api.models import OrderGroup, Order


class OrderGroupFilterset(filters.FilterSet):
    """Filter for Bookings by
    - active
    - code
    """

    active = filters.BooleanFilter(field_name="active", method="get_active")
    code = filters.CharFilter(field_name="code", method="get_code")

    def get_code(self, queryset, name, value):
        # DO exact match loookup from second character
        if value[1] == "-":
            return queryset.filter(code=value[2:].upper())
        else:
            return queryset.filter(code=value.upper())

    def get_active(self, queryset, name, value):
        return queryset.filter(
            Q(end_date=None) | Q(end_date__gt=datetime.datetime.now())
        )

    class Meta:
        model = OrderGroup
        fields = ["id", "user_address", "active", "code"]


class OrderFilterset(filters.FilterSet):
    """Filter for Events by code"""

    id = filters.CharFilter(field_name="id", lookup_expr="exact")
    order_group = filters.CharFilter(field_name="order_group", lookup_expr="exact")
    submitted_on = filters.BooleanFilter(
        field_name="submitted_on", lookup_expr="isnull"
    )
    code = filters.CharFilter(field_name="code", method="get_code")

    def get_code(self, queryset, name, value):
        # DO exact match loookup from second character
        if value[1] == "-":
            return queryset.filter(code=value[2:].upper())
        else:
            return queryset.filter(code=value.upper())

    class Meta:
        model = Order
        fields = ["id", "order_group", "submitted_on", "code"]
