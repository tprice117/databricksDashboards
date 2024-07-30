from django.contrib import admin

from api.models import Subscription


class SubscriptionInline(admin.StackedInline):
    model = Subscription
    fields = (
        "frequency",
        "service_day",
        "length",
        "subscription_number",
        "interval_days",
        "length_days",
    )
    show_change_link = True
    extra = 0
