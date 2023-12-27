from django.contrib import admin

from api.models import Product


class ProductInline(admin.TabularInline):
    model = Product
    fields = ("product_code", "description")
    show_change_link = True
    extra = 0
