from django.db import models


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
    sort = models.IntegerField(
        default=0,
    )
    tax = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        blank=True,
        null=True,
    )

    @property
    def total(self):
        if self.tax:
            return (float(self.quantity) * float(self.unit_price)) + float(self.tax)
        return float(self.quantity) * float(self.unit_price)

    class Meta:
        managed = False
