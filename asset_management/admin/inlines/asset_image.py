from django.contrib import admin

from asset_management.models import AssetImage


class AssetImageInline(admin.TabularInline):
    model = AssetImage
    fields = (
        "image",
        "image_tag",
        "created_on",
    )
    readonly_fields = (
        "created_on",
        "image_tag",
    )
    show_change_link = False
    extra = 0
    ordering = ("-created_on",)
