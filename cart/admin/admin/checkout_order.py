from django.contrib import admin

# Register your models here.
from admin_auto_filters.filters import AutocompleteFilter

from api.admin.filters import CreatedDateFilter
from cart.models import CheckoutOrder
from api.admin.inlines.order import OrderInline


class UserAddressFilter(AutocompleteFilter):
    title = "User Address"
    field_name = "user_address"


@admin.register(CheckoutOrder)
class CheckoutOrderAdmin(admin.ModelAdmin):
    model = CheckoutOrder
    list_display = (
        "user_address",
        "customer_price",
        "payment_method",
        "pay_later",
        "updated_on",
        "created_on",
    )
    ordering = ["-updated_on"]
    list_filter = [UserAddressFilter, CreatedDateFilter]
    inlines = [OrderInline]
    search_fields = [
        "created_by__email",
        "user_address__street",
        "user_address__city",
        "user_address__state",
        "user_address__postal_code",
    ]
    raw_id_fields = (
        "user_address",
        "payment_method",
        "created_by",
        "updated_by",
    )
