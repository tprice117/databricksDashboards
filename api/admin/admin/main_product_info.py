from django.contrib import admin
from import_export.admin import ExportActionMixin
from import_export import resources

from api.models import MainProductInfo
from common.admin.admin.base_admin import BaseModelAdmin


class MainProductInfoResource(resources.ModelResource):
    class Meta:
        model = MainProductInfo
        skip_unchanged = True


@admin.register(MainProductInfo)
class MainProductInfoAdmin(BaseModelAdmin, ExportActionMixin):
    resource_classes = [MainProductInfoResource]
    search_fields = ["id", "name", "main_product__name"]
    list_display = ("name", "main_product")
    raw_id_fields = ["main_product"]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "name",
                    "description",
                    "main_product",
                    "sort",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]
