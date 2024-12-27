from django.contrib import admin
from import_export.admin import ExportActionMixin
from import_export import resources

from api.admin.inlines import MainProductCategoryInline
from api.models import MainProductCategoryGroup
from common.admin.admin.base_admin import BaseModelAdmin


class MainProductCategoryGroupResource(resources.ModelResource):
    class Meta:
        model = MainProductCategoryGroup
        skip_unchanged = True


@admin.register(MainProductCategoryGroup)
class MainProductCategoryGroupAdmin(BaseModelAdmin, ExportActionMixin):
    resource_classes = [MainProductCategoryGroupResource]
    inlines = [
        MainProductCategoryInline,
    ]
    search_fields = ["id", "name"]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "name",
                    "sort",
                    "icon",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]
