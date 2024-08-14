from django.db import models

from api.models.main_product.main_product_waste_type import MainProductWasteType
from common.models import BaseModel


class PricingMaterialWasteType(BaseModel):
    main_product_waste_type = models.ForeignKey(MainProductWasteType, models.PROTECT)
    price_per_ton = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tonnage_included = models.IntegerField(default=0)

    class Meta:
        abstract = True
