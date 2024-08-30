from django.contrib import admin

from api.admin.filters import CreatedDateFilter
from cart.models import Cart
from cart.admin.inlines.cart_order import CartOrderInline


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    model = Cart
    list_display = ("active",)
    list_filter = [CreatedDateFilter, "active"]
    inlines = [CartOrderInline]
    search_fields = [
        "id",
        "created_by__email",
    ]
    raw_id_fields = ("user_addresses", "created_by", "updated_by")
