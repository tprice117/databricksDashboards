from django.db import models

from api.models.order.order_group import OrderGroup
from common.models import BaseModel


class OrderGroupRental(BaseModel):
    order_group = models.OneToOneField(
        OrderGroup, on_delete=models.CASCADE, related_name="rental"
    )
    included_days = models.IntegerField(default=0)
    price_per_day_included = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    price_per_day_additional = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
