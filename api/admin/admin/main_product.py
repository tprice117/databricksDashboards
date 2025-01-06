from django.contrib import admin
from import_export.admin import ExportActionMixin
from import_export import resources

from api.admin.inlines import (
    AddOnInline,
    MainProductImageInline,
    MainProductInfoInline,
    ProductInline,
)
from api.models import MainProduct
from common.admin.admin.base_admin import BaseModelAdmin


class MainProductResource(resources.ModelResource):
    class Meta:
        model = MainProduct
        skip_unchanged = True


@admin.register(MainProduct)
class MainProductAdmin(BaseModelAdmin, ExportActionMixin):
    resource_classes = [MainProductResource]
    search_fields = ["id", "name", "main_product_category__name"]
    list_display = ("name", "main_product_category", "sort", "_is_complete")
    change_form_template = "admin/api/mainproduct/change_form.html"
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "name",
                    "description",
                    "main_product_category",
                    "sort",
                    "main_product_code",
                ]
            },
        ),
        (
            "Images",
            {
                "fields": [
                    "image_del",
                    "ar_url",
                ]
            },
        ),
        (
            "Tags",
            {
                "fields": [
                    "tags",
                ]
            },
        ),
        (
            "Take Rate",
            {
                "fields": [
                    "default_take_rate",
                    "minimum_take_rate",
                    "max_discount",
                ]
            },
        ),
        (
            "Tonnage Configuration",
            {
                "fields": [
                    "included_tonnage_quantity",
                    "max_tonnage_quantity",
                ]
            },
        ),
        (
            "Pricing Model Configuration",
            {
                "fields": [
                    "has_rental",
                    "has_rental_one_step",
                    "has_rental_multi_step",
                    "has_service",
                    "has_service_times_per_week",
                    "has_material",
                    "allows_pick_up",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]
    readonly_fields = BaseModelAdmin.readonly_fields + [
        "max_discount",
    ]
    inlines = [
        ProductInline,
        MainProductImageInline,
        MainProductInfoInline,
        AddOnInline,
    ]
