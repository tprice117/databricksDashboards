from django.contrib import admin

from api.models import ProductAddOnChoice


class ProductAddOnChoiceInline(admin.TabularInline):
    model = ProductAddOnChoice
    fields = ("name", "product", "add_on_choice")
    show_change_link = True
    extra = 0
