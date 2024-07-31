import uuid

from django.db import models

from pricing_engine.models.pricing_line_item_group import PricingLineItemGroup


class PricingLineItem(models.Model):
    description = models.CharField(
        max_length=255,
        null=True,
    )
    quantity = models.IntegerField(
        default=1,
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    units = models.CharField(
        max_length=255,
        null=True,
    )

    @property
    def total(self):
        return self.quantity * self.unit_price

    class Meta:
        managed = False
