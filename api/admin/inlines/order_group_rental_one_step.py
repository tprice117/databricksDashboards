from django.contrib import admin

from api.models import OrderGroupRentalOneStep


class OrderGroupRentalOneStepInline(admin.TabularInline):
    model = OrderGroupRentalOneStep
    fields = ("rate",)
    show_change_link = True
    extra = 0
