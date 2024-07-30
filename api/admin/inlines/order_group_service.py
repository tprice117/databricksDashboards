from django.contrib import admin

from api.models import OrderGroupService


class OrderGroupServiceInline(admin.TabularInline):
    model = OrderGroupService
    fields = ("rate", "miles")
    show_change_link = True
    extra = 0
