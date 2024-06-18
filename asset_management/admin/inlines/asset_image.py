from django.contrib import admin

from asset_management.models import AssetImage


class AssetImageInline(admin.TabularInline):
    model = AssetImage
    fields = (
        "image",
        "created_on",
    )
    show_change_link = False
    extra = 0
    ordering = ("-created_on",)
