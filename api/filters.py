import datetime
from django_filters import rest_framework as filters
from django.db.models import Q

from api.models import OrderGroup, Order


class ListFilter(filters.Filter):
    def filter(self, qs, value):
        if not value:
            return qs

        self.lookup_expr = "in"
        values = value.split(",")
        return super(ListFilter, self).filter(qs, values)


class OrderGroupFilterset(filters.FilterSet):
    """Filter for Bookings by
    - id
    - user
    - user_address
    - active
    - code
    - status
    - search
    """

    active = filters.BooleanFilter(
        field_name="active", method="get_active", help_text="Filter active bookings"
    )
    code = filters.CharFilter(field_name="code", method="get_code")
    status = ListFilter(
        field_name="orders__status",
        help_text="Get bookings that have order status. Comma separated list of statuses.",
    )
    search = filters.CharFilter(
        field_name="search",
        method="get_search",
        help_text="Search user email, first name, last name, booking address, seller name, seller location name, product name",
    )

    def get_search(self, queryset, name, value):
        """Search by user email, first name, last name, booking address, seller name, seller location name, product name"""
        # search by address, seller, user, product

        if not value:
            return queryset.all()
        # Q(code__icontains=value)
        return queryset.filter(
            Q(user__email__icontains=value)
            | Q(user__first_name__icontains=value)
            | Q(user__last_name__icontains=value)
            | Q(user_address__name__icontains=value)
            | Q(user_address__street__icontains=value)
            | Q(user_address__city__icontains=value)
            | Q(user_address__state__icontains=value)
            | Q(user_address__postal_code__icontains=value)
            | Q(seller_product_seller_location__seller_location__name__icontains=value)
            | Q(
                seller_product_seller_location__seller_location__seller__name__icontains=value
            )
            | Q(
                seller_product_seller_location__seller_product__product__main_product__name__icontains=value
            )
        )

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
        fields = {
            "id": ["exact"],
            "user": ["in"],
            "user_address": ["exact"],
            # The order status filter could be added like this, but the docs don't show the enum values
            # "orders__status": ["in"],
        }


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
