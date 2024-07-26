from django.contrib import admin

from api.models import AddOn


class AddOnInline(admin.TabularInline):
    model = AddOn
    fields = (
        "name",
        "sort",
    )
    show_change_link = True
    extra = 0
