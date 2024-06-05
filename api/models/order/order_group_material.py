from django.db import models

from api.models.order.order_group import OrderGroup
from common.models import BaseModel


class OrderGroupMaterial(BaseModel):
    order_group = models.OneToOneField(
        OrderGroup, on_delete=models.CASCADE, related_name="material"
    )
    price_per_ton = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    tonnage_included = models.IntegerField(default=0)

    def update_pricing(self):
        """
        Based on the OrderGroup.SellerProductSellerLocation's pricing, update the pricing.
        """
        self.price_per_ton = (
            self.order_group.seller_product_seller_location.material.price_per_ton
        )
        self.tonnage_included = (
            self.order_group.seller_product_seller_location.material.tonnage_included
        )
        self.save()
