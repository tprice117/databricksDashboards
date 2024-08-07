from django.db import models

from api.models.main_product.main_product_waste_type import MainProductWasteType
from common.models import BaseModel


class SellerProductSellerLocationMaterialWasteType(BaseModel):
    seller_product_seller_location_material = models.ForeignKey(
        "api.SellerProductSellerLocationMaterial",
        models.PROTECT,
        related_name="waste_types",
    )
    main_product_waste_type = models.ForeignKey(MainProductWasteType, models.PROTECT)
    price_per_ton = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tonnage_included = models.IntegerField(default=0)

    class Meta:
        unique_together = (
            "seller_product_seller_location_material",
            "main_product_waste_type",
        )

    @property
    def base_price(self):
        return (
            self.price_per_ton
            * self.seller_product_seller_location_material.seller_product_seller_location.seller_product.product.main_product.included_tonnage_quantity
        )
