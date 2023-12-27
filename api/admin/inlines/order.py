from django.contrib import admin

from api.models import Order


class OrderInline(admin.TabularInline):
    model = Order
    fields = ("start_date", "end_date", "service_date", "submitted_on")
    show_change_link = True
    extra = 0
