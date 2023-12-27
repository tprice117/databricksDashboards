from django.contrib import admin

from api.models import MainProductInfo


@admin.register(MainProductInfo)
class MainProductInfoAdmin(admin.ModelAdmin):
    search_fields = ["name", "main_product__name"]
    list_display = ("name", "main_product")
