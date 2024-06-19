from django.contrib import admin

from asset_management.models import AssetReplacementValue


class AssetReplacementValueInline(admin.TabularInline):
    model = AssetReplacementValue
    fields = (
        "replacement_value",
        "created_on",
    )
    readonly_fields = ("created_on",)
    show_change_link = False
    extra = 0
    ordering = ("-created_on",)
