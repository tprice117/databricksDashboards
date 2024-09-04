import datetime
from django_filters import rest_framework as filters
from django.db.models import Q

from api.models import OrderGroup


class OrderGroupFilterset(filters.FilterSet):
    """Filter for Books by if books are published or not"""

    active = filters.BooleanFilter(field_name="active", method="get_active")

    def get_active(self, queryset, name, value):
        return queryset.filter(
            Q(end_date=None) | Q(end_date__gt=datetime.datetime.now())
        )

    class Meta:
        model = OrderGroup
        fields = ["id", "user_address", "active"]
