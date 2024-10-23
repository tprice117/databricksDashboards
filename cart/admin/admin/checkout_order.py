from django.contrib import admin
from django.conf import settings
from django.shortcuts import render

# Register your models here.
from admin_auto_filters.filters import AutocompleteFilter

from api.admin.filters import CreatedDateFilter
from cart.models import CheckoutOrder
from api.admin.inlines.order import OrderInline
from cart.utils import QuoteUtils


class UserAddressFilter(AutocompleteFilter):
    title = "User Address"
    field_name = "user_address"


@admin.register(CheckoutOrder)
class CheckoutOrderAdmin(admin.ModelAdmin):
    model = CheckoutOrder
    actions = ["show_quote"]
    list_display = (
        "user_address",
        "customer_price",
        "estimated_taxes",
        "price",
        "pay_later",
        "quote_expiration",
        "updated_on",
        "created_on",
    )
    ordering = ["-updated_on"]
    list_filter = ["pay_later", UserAddressFilter, CreatedDateFilter]
    inlines = [OrderInline]
    search_fields = [
        "id",
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

    @admin.action(description="Show Quote")
    def show_quote(self, request, queryset):
        checkout_order = queryset.first()
        order_id_lst = []
        for order in checkout_order.orders.all():
            order_id_lst.append(order.id)
        checkout_order = QuoteUtils.create_quote(order_id_lst, None, quote_sent=False)
        payload = {"trigger": checkout_order.get_quote()}
        payload["trigger"][
            "accept_url"
        ] = f"{settings.BASE_URL}/cart/{checkout_order.user_address_id}/"
        return render(request, "customer_dashboard/customer_quote.html", payload)
