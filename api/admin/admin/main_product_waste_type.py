from django.contrib import admin
from import_export.admin import ExportActionMixin
from import_export import resources

from api.models import MainProductWasteType
from common.admin.admin.base_admin import BaseModelAdmin


class MainProductWasteTypeResource(resources.ModelResource):
    class Meta:
        model = MainProductWasteType
        skip_unchanged = True


@admin.register(MainProductWasteType)
class MainProductWasteTypeAdmin(BaseModelAdmin, ExportActionMixin):
    resource_classes = [MainProductWasteTypeResource]
    model = MainProductWasteType
    search_fields = ["id", "main_product__name", "waste_type__name"]
    raw_id_fields = ["main_product"]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "waste_type",
                    "main_product",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]
