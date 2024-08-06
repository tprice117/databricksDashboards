from django.db import models

from common.models import BaseModel


class OrderGroupRentalMultiStep(BaseModel):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="rental_multi_step",
    )
    hour = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    day = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    week = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    two_weeks = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    month = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
