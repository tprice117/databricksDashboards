from django.contrib import admin
from import_export.admin import ExportActionMixin
from import_export import resources

from api.admin.inlines import ProductAddOnChoiceInline, SellerProductInline
from api.models import Product
from common.admin.admin.base_admin import BaseModelImportExportAdmin


class ProductResource(resources.ModelResource):
    class Meta:
        model = Product


@admin.register(Product)
class ProductAdmin(BaseModelImportExportAdmin, ExportActionMixin):
    resource_classes = [ProductResource]
    search_fields = ["description", "main_product__name"]
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
        BaseModelImportExportAdmin.audit_fieldset,
    ]
