from django.contrib import admin

from api.models import MainProductCategory


class MainProductCategoryInline(admin.TabularInline):
    model = MainProductCategory
    fields = ("name",)
    readonly_fields = ("name",)
    show_change_link = True
    extra = 0
    max_num = 0
