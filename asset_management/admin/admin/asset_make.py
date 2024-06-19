from django.contrib import admin

from asset_management.admin.inlines import AssetModelInline
from asset_management.models import AssetMake


@admin.register(AssetMake)
class AssetMakeAdmin(admin.ModelAdmin):
    search_fields = [
        "name",
    ]
    list_display = ("name",)
    inlines = [
        AssetModelInline,
    ]
