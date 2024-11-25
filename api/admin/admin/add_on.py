from django.contrib import admin
from import_export.admin import ExportActionMixin
from import_export import resources

from api.admin.inlines import AddOnChoiceInline
from api.models import AddOn
from common.admin.admin.base_admin import BaseModelAdmin


class AddOnResource(resources.ModelResource):
    class Meta:
        model = AddOn
        skip_unchanged = True


@admin.register(AddOn)
class AddOnAdmin(BaseModelAdmin, ExportActionMixin):
    resource_classes = [AddOnResource]
    inlines = [
        AddOnChoiceInline,
    ]
    search_fields = ["id", "name", "main_product__name"]
    raw_id_fields = ["main_product"]

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "main_product",
                    "name",
                    "sort",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]
