from django.contrib import admin

from api.admin.inlines import ProductAddOnChoiceInline
from api.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    search_fields = ["description", "main_product__name"]
    list_display = ("__str__", "main_product")
    inlines = [
        ProductAddOnChoiceInline,
    ]
