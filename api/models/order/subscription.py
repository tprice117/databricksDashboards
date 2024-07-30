from django.db import models

from api.models.day_of_week import DayOfWeek
from api.models.order.order_group import OrderGroup
from api.models.service_recurring_freqency import ServiceRecurringFrequency
from common.models import BaseModel


class Subscription(BaseModel):
    order_group = models.OneToOneField(OrderGroup, models.PROTECT)
    frequency = models.ForeignKey(
        ServiceRecurringFrequency, models.PROTECT, blank=True, null=True
    )
    service_day = models.ForeignKey(DayOfWeek, models.PROTECT, blank=True, null=True)
    length = models.IntegerField()
    subscription_number = models.CharField(max_length=255)
    interval_days = models.IntegerField(blank=True, null=True)
    length_days = models.IntegerField(blank=True, null=True)
