from django.db import models

from common.models import BaseModel


class OrderGroupMaterial(BaseModel):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="material",
    )
    price_per_ton = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tonnage_included = models.IntegerField(default=0)

    def update_pricing(self):
        """
        Based on the OrderGroup.SellerProductSellerLocation's pricing, update the pricing.
        """
        material_waste_type = (
            self.order_group.seller_product_seller_location.material.waste_types.filter(
                main_product_waste_type__waste_type=self.order_group.waste_type
            ).first()
        )
        self.price_per_ton = material_waste_type.price_per_ton
        self.tonnage_included = material_waste_type.tonnage_included
        self.save()
