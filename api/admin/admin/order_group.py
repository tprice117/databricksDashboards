from django.contrib import admin

from api.admin.filters import CreatedDateFilter
from api.admin.inlines import (
    OrderGroupMaterialInline,
    OrderGroupRentalInline,
    OrderGroupServiceInline,
    OrderInline,
    SubscriptionInline,
)
from api.models import OrderGroup


@admin.register(OrderGroup)
class OrderGroupAdmin(admin.ModelAdmin):
    model = OrderGroup
    list_display = ("user", "user_address", "seller_product_seller_location")
    list_filter = (CreatedDateFilter,)
    autocomplete_fields = [
        "seller_product_seller_location",
    ]
    inlines = [
        SubscriptionInline,
        OrderInline,
        OrderGroupServiceInline,
        OrderGroupRentalInline,
        OrderGroupMaterialInline,
    ]
    search_fields = [
        "user__email",
        "user_address__street",
        "user_address__city",
        "user_address__state",
        "user_address__postal_code",
    ]
