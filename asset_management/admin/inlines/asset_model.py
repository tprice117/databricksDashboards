from django.contrib import admin

from asset_management.models import AssetModel


class AssetModelInline(admin.TabularInline):
    model = AssetModel
    fields = ("name",)
    show_change_link = True
    extra = 0
