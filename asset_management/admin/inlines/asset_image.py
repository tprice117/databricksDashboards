from django.contrib import admin

from asset_management.models import AssetImage


class AssetImageInline(admin.TabularInline):
    model = AssetImage
    fields = ("image",)
    readonly_fields = ("image",)
    show_change_link = False
    extra = 0
    ordering = ("-created_on",)
