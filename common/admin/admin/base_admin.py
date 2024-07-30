from django.contrib import admin


class BaseModelAdmin(admin.ModelAdmin):
    """
    The base model admin class
    """

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
