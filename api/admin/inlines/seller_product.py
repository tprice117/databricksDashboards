from django.contrib import admin

from api.models import SellerProduct


class SellerProductInline(admin.TabularInline):
    model = SellerProduct
    fields = ("product",)
    show_change_link = True
    extra = 0
    raw_id_fields = ("product",)
