from django.db import models

from api.models.common.material_waste_type import PricingMaterialWasteType


class OrderGroupMaterialWasteType(PricingMaterialWasteType):
    order_group_material = models.ForeignKey(
        "api.OrderGroupMaterial",
        models.PROTECT,
        related_name="waste_types",
    )

    class Meta:
        unique_together = (
            "order_group_material",
            "main_product_waste_type",
        )

    @property
    def base_price(self):
        return (
            self.price_per_ton * self.order_group_material.order_group.tonnage_quantity
        )
