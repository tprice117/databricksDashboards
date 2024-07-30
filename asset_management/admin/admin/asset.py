from django.contrib import admin

from asset_management.admin.inlines import (
    AssetHoursInline,
    AssetImageInline,
    AssetReplacementValueInline,
)
from asset_management.models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    search_fields = [
        "name",
        "serial_number",
    ]
    list_display = (
        "seller_location",
        "year",
        "model",
        "serial_number",
    )
    autocomplete_fields = [
        "seller_location",
        "model",
    ]
    inlines = [
        AssetHoursInline,
        AssetImageInline,
        AssetReplacementValueInline,
    ]
