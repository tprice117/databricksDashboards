from django.contrib import admin
from import_export import resources
from import_export.admin import ExportActionMixin

from common.admin.admin.base_admin import BaseModelAdmin
from permits.models import Permit


class PermitResource(resources.ModelResource):
    class Meta:
        model = Permit
        skip_unchanged = True


@admin.register(Permit)
class PermitAdmin(BaseModelAdmin, ExportActionMixin):
    resource_classes = [PermitResource]
    search_fields = [
        "id",
        "name",
    ]
    list_display = ("name", "description")

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "name",
                    "description",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]
