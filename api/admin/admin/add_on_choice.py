from django.contrib import admin
from import_export.admin import ExportActionMixin
from import_export import resources

from api.models import AddOnChoice
from common.admin.admin.base_admin import BaseModelAdmin


class AddOnChoiceResource(resources.ModelResource):
    class Meta:
        model = AddOnChoice
        skip_unchanged = True


@admin.register(AddOnChoice)
class AddOnChoiceAdmin(BaseModelAdmin, ExportActionMixin):
    resource_classes = [AddOnChoiceResource]
    search_fields = ["id", "name", "add_on__name"]
    list_display = ("name", "add_on")
    raw_id_fields = ["add_on"]

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "add_on",
                    "name",
                ]
            },
        ),
        BaseModelAdmin.audit_fieldset,
    ]
