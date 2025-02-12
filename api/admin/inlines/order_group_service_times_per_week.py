from django.contrib import admin

from api.models import OrderGroupServiceTimesPerWeek


class OrderGroupServiceTimesPerWeekInline(admin.TabularInline):
    model = OrderGroupServiceTimesPerWeek
    fields = (
        "one_every_other_week",
        "one_time_per_week",
        "two_times_per_week",
        "three_times_per_week",
        "four_times_per_week",
        "five_times_per_week",
    )
    show_change_link = True
    extra = 0
