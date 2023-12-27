from django.contrib import admin

from api.models import AddOnChoice


class AddOnChoiceInline(admin.TabularInline):
    model = AddOnChoice
    fields = ("name",)
    show_change_link = True
    extra = 0
