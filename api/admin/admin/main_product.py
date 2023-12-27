from django.contrib import admin

from api.admin.inlines import MainProductInfoInline, ProductInline
from api.models import MainProduct


@admin.register(MainProduct)
class MainProductAdmin(admin.ModelAdmin):
    search_fields = ["name", "main_product_category__name"]
    list_display = ("name", "main_product_category", "sort")
    inlines = [
        ProductInline,
        MainProductInfoInline,
    ]
