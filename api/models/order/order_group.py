from django.db import models

from api.models.day_of_week import DayOfWeek
from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from api.models.service_recurring_freqency import ServiceRecurringFrequency
from api.models.time_slot import TimeSlot
from api.models.user.user_address import UserAddress
from api.models.waste_type import WasteType
from common.models import BaseModel


class OrderGroup(BaseModel):
    user = models.ForeignKey("api.User", models.PROTECT)
    user_address = models.ForeignKey(
        UserAddress,
        models.PROTECT,
        related_name="order_groups",
    )
    seller_product_seller_location = models.ForeignKey(
        SellerProductSellerLocation, models.PROTECT
    )
    waste_type = models.ForeignKey(WasteType, models.PROTECT, blank=True, null=True)
    time_slot = models.ForeignKey(TimeSlot, models.PROTECT, blank=True, null=True)
    access_details = models.TextField(blank=True, null=True)
    placement_details = models.TextField(blank=True, null=True)
    service_recurring_frequency = models.ForeignKey(
        ServiceRecurringFrequency, models.PROTECT, blank=True, null=True
    )
    preferred_service_days = models.ManyToManyField(DayOfWeek, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    take_rate = models.DecimalField(max_digits=18, decimal_places=2, default=30)
    tonnage_quantity = models.IntegerField(blank=True, null=True)
    delivery_fee = models.DecimalField(
        max_digits=18, decimal_places=2, default=0, blank=True, null=True
    )
    removal_fee = models.DecimalField(
        max_digits=18, decimal_places=2, default=0, blank=True, null=True
    )

    def __str__(self):
        return f'{self.user.user_group.name if self.user.user_group else ""} - {self.user.email} - {self.seller_product_seller_location.seller_location.seller.name}'
