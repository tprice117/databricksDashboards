from django.contrib import admin


class BaseModelStackedInline(admin.StackedInline):
    readonly_fields = [
        "created_on",
        "created_by",
        "updated_on",
        "updated_by",
    ]
