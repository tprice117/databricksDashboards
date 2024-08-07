from django.db import models

from common.models import BaseModel


class OrderGroupRentalOneStep(BaseModel):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="rental_one_step",
    )
    rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
