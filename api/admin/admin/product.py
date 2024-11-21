from django.contrib import admin
from import_export.admin import ExportActionMixin
from import_export import resources

from api.admin.inlines import ProductAddOnChoiceInline, SellerProductInline
from api.models import Product
from common.admin.admin.base_admin import BaseModelAdmin


class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        skip_unchanged = True


@admin.register(Product)
class ProductAdmin(BaseModelAdmin, ExportActionMixin):
    resource_classes = [ProductResource]
    search_fields = ["description", "main_product__name"]
    raw_id_fields = ["main_product"]
    list_display = ("__str__", "main_product")
    inlines = [ProductAddOnChoiceInline, SellerProductInline]
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
