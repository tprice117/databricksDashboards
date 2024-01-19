from django.db import models

from api.models.order.order_group import OrderGroup
from common.models import BaseModel


class OrderGroupService(BaseModel):
    order_group = models.OneToOneField(
        OrderGroup, on_delete=models.CASCADE, related_name="service"
    )
    rate = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    miles = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
