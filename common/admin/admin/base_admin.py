from django.contrib import admin


class BaseModelAdmin(admin.ModelAdmin):
    """
    The base model admin class
    """

    readonly_fields = [
        "created_on",
        "created_by",
        "updated_on",
        "updated_by",
    ]
