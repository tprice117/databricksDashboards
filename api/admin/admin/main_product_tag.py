from django.contrib import admin

from api.models import MainProductTag


@admin.register(MainProductTag)
class MainProductTagAdmin(admin.ModelAdmin):
    search_fields = [
        "name",
    ]
    list_display = ("name",)
