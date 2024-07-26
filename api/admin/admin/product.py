from django.contrib import admin

from api.admin.inlines import (
    ProductAddOnChoiceInline,
    # SellerProductSellerLocationInline,
)
from api.models import Product
from common.admin.admin.base_admin import BaseModelAdmin


@admin.register(Product)
class ProductAdmin(BaseModelAdmin):
    search_fields = ["description", "main_product__name"]
    list_display = ("__str__", "main_product")
    inlines = [
        ProductAddOnChoiceInline,
        # NOTE: Product needs a foreign key to SellerProductSellerLocation inorder to use this inline.
        # SellerProductSellerLocationInline,
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
