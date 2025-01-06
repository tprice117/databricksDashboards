from django.contrib import admin

from api.models import Order


class OrderInline(admin.TabularInline):
    model = Order
    fields = (
        "start_date",
        "end_date",
        "order_type",
        "submitted_on",
    )
    readonly_fields = ("order_type",)
    ordering = (
        "created_on",
        "start_date",
    )
    show_change_link = True
    extra = 0
