from django.contrib import admin
from import_export.admin import ExportActionMixin
from import_export import resources

from api.admin.inlines import MainProductCategoryInfoInline, MainProductInline
from api.models import MainProductCategory
from common.admin.admin.base_admin import BaseModelAdmin


class MainProductCategoryResource(resources.ModelResource):
    class Meta:
        model = MainProductCategory
        skip_unchanged = True


@admin.register(MainProductCategory)
class MainProductCategoryAdmin(BaseModelAdmin, ExportActionMixin):
    resource_classes = [MainProductCategoryResource]
    inlines = [
        MainProductInline,
        MainProductCategoryInfoInline,
    ]
    search_fields = [
        "id",
        "name",
        "description",
        "main_product_category_code",
        "group__name",
        "industry",
    ]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "group",
                    "name",
                    "industry",
                    "description",
                    "image2",
                    "icon",
                    "main_product_category_code",
                    "sort",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]
