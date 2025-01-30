from django.contrib import admin

from api.models import MainProductInfo


class MainProductInfoInline(admin.TabularInline):
    model = MainProductInfo
    fields = (
        "name",
        "description",
        "sort",
    )
    show_change_link = True
    extra = 0
