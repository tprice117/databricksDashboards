from django.db import models

from api.models.main_product.main_product import MainProduct
from common.models import BaseModel


class AddOn(BaseModel):
    main_product = models.ForeignKey(
        MainProduct,
        models.CASCADE,
        related_name="add_ons",
    )
    name = models.CharField(max_length=80)
    sort = models.DecimalField(
        max_digits=18,
        decimal_places=0,
    )

    def __str__(self):
        return f"{self.main_product.name} - {self.name}"

    class Meta:
        verbose_name = "Variant"
        verbose_name_plural = "Variants"
