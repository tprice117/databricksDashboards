from admin_auto_filters.filters import AutocompleteFilter
from django.contrib import admin

from api.admin.filters import CreatedDateFilter
from api.admin.inlines import (
    OrderGroupMaterialInline,
    OrderGroupRentalInline,
    OrderGroupRentalMultiStepInline,
    OrderGroupRentalOneStepInline,
    OrderGroupServiceInline,
    OrderGroupServiceTimesPerWeekInline,
    OrderGroupAttachmentInline,
    OrderInline,
    SubscriptionInline,
)
from api.models import OrderGroup


class UserAddressFilter(AutocompleteFilter):
    title = "User Address"
    field_name = "user_address"


@admin.register(OrderGroup)
class OrderGroupAdmin(admin.ModelAdmin):
    model = OrderGroup
    list_display = (
        "user",
        "user_address",
        "seller_product_seller_location",
    )
    list_filter = [
        UserAddressFilter,
        CreatedDateFilter,
    ]
    autocomplete_fields = [
        "seller_product_seller_location",
    ]
    inlines = [
        SubscriptionInline,
        OrderInline,
        OrderGroupRentalOneStepInline,
        OrderGroupRentalInline,
        OrderGroupRentalMultiStepInline,
        OrderGroupServiceTimesPerWeekInline,
        OrderGroupServiceInline,
        OrderGroupMaterialInline,
        OrderGroupAttachmentInline,
    ]
    search_fields = [
        "id",
        "user__email",
        "user_address__street",
        "user_address__city",
        "user_address__state",
        "user_address__postal_code",
    ]
    raw_id_fields = ("user", "user_address", "conversation", "created_by", "updated_by")
