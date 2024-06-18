from django.contrib import admin

from asset_management.models import AssetHours


class AssetHoursInline(admin.TabularInline):
    model = AssetHours
    fields = ("hours",)
    readonly_fields = ("hours",)
    show_change_link = False
    extra = 0
    ordering = ("-created_on",)
