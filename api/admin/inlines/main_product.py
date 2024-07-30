from django.contrib import admin

from api.models import MainProduct


class MainProductInline(admin.TabularInline):
    model = MainProduct
    fields = ("name",)
    show_change_link = True
    extra = 0
