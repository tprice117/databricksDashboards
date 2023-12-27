from django.contrib import admin

from api.models import AddOnChoice


@admin.register(AddOnChoice)
class AddOnChoiceAdmin(admin.ModelAdmin):
    search_fields = ["name", "add_on__name"]
    list_display = ("name", "add_on")
