from django.contrib import admin

from api.models import Product


class ProductInline(admin.TabularInline):
    model = Product
    fields = ("product_code", "formatted_add_on_choices")
    readonly_fields = ("formatted_add_on_choices",)
    show_change_link = True
    extra = 0

    def formatted_add_on_choices(self, obj: Product):
        return obj.formatted_add_on_choices
