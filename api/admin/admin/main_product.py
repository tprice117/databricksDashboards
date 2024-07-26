from django.contrib import admin

from api.admin.inlines import AddOnInline, MainProductInfoInline, ProductInline
from api.models import MainProduct


@admin.register(MainProduct)
class MainProductAdmin(admin.ModelAdmin):
    search_fields = ["name", "main_product_category__name"]
    list_display = ("name", "main_product_category", "sort", "_is_complete")
    inlines = [
        ProductInline,
        MainProductInfoInline,
        AddOnInline,
    ]
