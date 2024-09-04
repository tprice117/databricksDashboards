from django.db import models

from api.models.main_product.main_product import MainProduct
from api.models.waste_type import WasteType
from common.models import BaseModel


class MainProductWasteType(BaseModel):
    waste_type = models.ForeignKey(WasteType, models.CASCADE)
    main_product = models.ForeignKey(MainProduct, models.CASCADE)

    def __str__(self):
        return f"{self.main_product.name} - {self.waste_type.name}"

    class Meta:
        unique_together = (
            "waste_type",
            "main_product",
        )

    class Meta:
        verbose_name = "Product Waste Type"
        verbose_name_plural = "Product Waste Types"
