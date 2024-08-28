from django.contrib import admin

from cart.models import CartOrder


class CartOrderInline(admin.TabularInline):
    model = CartOrder
    fields = ("user_address", "payment_method", "pay_later", "quote_accepted_at")
    raw_id_fields = ("user_address",)
    show_change_link = True
    extra = 0
