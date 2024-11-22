from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export.tmp_storages import MediaStorage


class BaseModelAdmin(ImportExportModelAdmin):
    """
    The base model admin class
    """

    tmp_storage_class = MediaStorage

    audit_fields = [
        "created_on",
        "created_by",
        "updated_on",
        "updated_by",
    ]
    audit_fieldset = (
        "Audit",
        {
            "fields": audit_fields,
            "classes": ["collapse"],
        },
    )
    readonly_fields = audit_fields
