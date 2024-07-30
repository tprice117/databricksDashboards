from django.contrib import admin

from api.models import OrderGroupRental


class OrderGroupRentalInline(admin.TabularInline):
    model = OrderGroupRental
    fields = ("included_days", "price_per_day_included", "price_per_day_additional")
    show_change_link = True
    extra = 0
