from django.contrib import admin

from api.models import MainProductWasteType


@admin.register(MainProductWasteType)
class MainProductWasteTypeAdmin(admin.ModelAdmin):
    model = MainProductWasteType
    search_fields = ["main_product__name", "waste_type__name"]
