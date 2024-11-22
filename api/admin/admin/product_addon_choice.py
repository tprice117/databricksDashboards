from django.contrib import admin
from import_export.admin import ExportActionMixin
from import_export import resources

from api.models import ProductAddOnChoice
from common.admin.admin.base_admin import BaseModelAdmin


class ProductAddOnChoiceResource(resources.ModelResource):
    class Meta:
        model = ProductAddOnChoice
        skip_unchanged = True


@admin.register(ProductAddOnChoice)
class ProductAddOnChoiceAdmin(BaseModelAdmin, ExportActionMixin):
    resource_classes = [ProductAddOnChoiceResource]
    search_fields = (
        "id",
        "name",
        "product__main_product__name",
        "add_on_choice__name",
        "add_on_choice__add_on__name",
    )
    list_display = ("__str__",)
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "name",
                    "product",
                    "add_on_choice",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]
    raw_id_fields = ["product", "add_on_choice"]
