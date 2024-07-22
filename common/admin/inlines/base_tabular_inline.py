from django.contrib import admin


class BaseModelTabularInline(admin.TabularInline):
    readonly_fields = [
        "created_on",
        "created_by",
        "updated_on",
        "updated_by",
    ]
