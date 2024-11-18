from django.contrib import admin

from api.models import ProductAddOnChoice
from common.admin.admin.base_admin import BaseModelAdmin


@admin.register(ProductAddOnChoice)
class ProductAddOnChoiceAdmin(BaseModelAdmin):
    search_fields = ["name", "product__main_product__name"]
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
