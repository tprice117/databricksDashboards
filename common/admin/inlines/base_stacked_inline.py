from django.contrib import admin


class BaseModelStackedInline(admin.StackedInline):
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
    readonly_fields = [
        "created_on",
        "created_by",
        "updated_on",
        "updated_by",
    ]
