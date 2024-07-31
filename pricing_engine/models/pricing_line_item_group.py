import uuid

from django.db import models


class PricingLineItemGroup(models.Model):
    title = models.CharField(
        max_length=255,
    )

    @property
    def total(self):
        return sum([item.total for item in self.items.all()])

    class Meta:
        managed = False
