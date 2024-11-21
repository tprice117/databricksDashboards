from django.contrib import admin

from api.models import AddOnChoice


class AddOnChoiceInline(admin.TabularInline):
    model = AddOnChoice
    fields = ("name",)
    search_fields = ["id", "name", "add_on__name", "add_on__main_product__name"]
    show_change_link = True
    extra = 0
