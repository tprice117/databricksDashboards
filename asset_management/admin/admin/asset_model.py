from django.contrib import admin

from asset_management.models import AssetModel


@admin.register(AssetModel)
class AssetModelAdmin(admin.ModelAdmin):
    search_fields = [
        "name",
        "asset_model__name",
    ]
    list_display = (
        "asset_make__name",
        "name",
    )

    def has_module_permission(self, request):
        return False
