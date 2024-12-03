from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ExportActionMixin
from import_export import resources

from api.models import Industry


class IndustryResource(resources.ModelResource):
    class Meta:
        model = Industry
        skip_unchanged = True


@admin.register(Industry)
class IndustryAdmin(ImportExportModelAdmin, ExportActionMixin):
    resource_classes = [IndustryResource]
    search_fields = [
        "id",
        "name",
        "description",
    ]
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "name",
                    "description",
                    "image",
                    "sort",
                ]
            },
        ),
    ]
