from django.contrib import admin

from asset_management.models import AssetReplacementValue


class AssetReplacementValueInline(admin.TabularInline):
    model = AssetReplacementValue
    fields = ("replacement_value",)
    readonly_fields = ("replacement_value",)
    show_change_link = False
    extra = 0
    ordering = ("-created_on",)
