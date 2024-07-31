import uuid

from django.db import models


class PricingLineItem(models.Model):
    description = models.CharField(
        max_length=255,
    )
    quantity = models.IntegerField()
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    units = models.CharField(
        max_length=255,
    )

    def total(self):
        return self.quantity * self.unit_price

    class Meta:
        abstract = True
