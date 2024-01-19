from django.db import models

from api.models.order.order_group import OrderGroup
from common.models import BaseModel


class OrderGroupMaterial(BaseModel):
    order_group = models.OneToOneField(
        OrderGroup, on_delete=models.CASCADE, related_name="material"
    )
    price_per_ton = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tonnage_included = models.IntegerField(default=0)
