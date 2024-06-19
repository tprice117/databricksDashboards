from django.db import models

from api.models.main_product.main_product import MainProduct
from asset_management.models.asset_make import AssetMake
from common.models import BaseModel


class AssetModel(BaseModel):
    asset_make = models.ForeignKey(
        AssetMake,
        on_delete=models.CASCADE,
    )
    main_product = models.ForeignKey(
        MainProduct,
        on_delete=models.PROTECT,
    )
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.asset_make} {self.name} - {self.main_product}"
