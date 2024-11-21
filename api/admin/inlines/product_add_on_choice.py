from django.contrib import admin

from api.models import ProductAddOnChoice


class ProductAddOnChoiceInline(admin.TabularInline):
    model = ProductAddOnChoice
    search_fields = (
        "id",
        "name",
        "product__main_product__name",
        "add_on_choice__name",
        "add_on_choice__add_on__name",
    )
    fields = ("product", "add_on_choice")
    raw_id_fields = ("product", "add_on_choice")
    autocomplete_fields = ["product", "add_on_choice"]
    show_change_link = True
    extra = 0
