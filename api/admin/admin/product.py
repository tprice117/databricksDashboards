from django.contrib import admin

from api.admin.inlines import ProductAddOnChoiceInline
from api.models import Product
from common.admin.admin.base_admin import BaseModelAdmin


@admin.register(Product)
class ProductAdmin(BaseModelAdmin):
    search_fields = ["description", "main_product__name"]
    list_display = ("__str__", "main_product")
    inlines = [
        ProductAddOnChoiceInline,
    ]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "main_product",
                    "product_code",
                    "description",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]
