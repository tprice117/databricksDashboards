from django.db import models


class PricingLineItemGroup(models.Model):
    title = models.CharField(
        max_length=255,
    )
    code = models.CharField(
        max_length=255,
    )
    sort = models.IntegerField(
        default=0,
    )

    class Meta:
        managed = False
