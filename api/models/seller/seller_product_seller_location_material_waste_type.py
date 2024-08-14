from django.db import models

from api.models.common.material_waste_type import PricingMaterialWasteType


class SellerProductSellerLocationMaterialWasteType(PricingMaterialWasteType):
    seller_product_seller_location_material = models.ForeignKey(
        "api.SellerProductSellerLocationMaterial",
        models.PROTECT,
        related_name="waste_types",
    )

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
