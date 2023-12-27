from django.contrib import admin

from api.models import MainProductCategoryInfo


class MainProductCategoryInfoInline(admin.TabularInline):
    model = MainProductCategoryInfo
    fields = ("name",)
    show_change_link = True
    extra = 0
