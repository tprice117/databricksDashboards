import uuid

from django.db import models

from pricing_engine.models import PricingLineItem


class PricingLineItemGroup(models.Model):
    title = models.CharField(
        max_length=255,
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    items = models.ManyToManyField(
        PricingLineItem,
        related_name="items",
    )

    @property
    def total(self):
        return sum([item.total for item in self.items.all()])

    class Meta:
        abstract = True
