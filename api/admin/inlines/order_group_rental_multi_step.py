from django.contrib import admin

from api.models import OrderGroupRentalMultiStep


class OrderGroupRentalMultiStepInline(admin.TabularInline):
    model = OrderGroupRentalMultiStep
    fields = (
        "month",
        "two_weeks",
        "week",
        "day",
        "hour",
    )
    show_change_link = True
    extra = 0
