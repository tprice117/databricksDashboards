from typing import List

from django.db import models

from api.models.order.order import Order
from api.models.order.order_line_item import OrderLineItem
from api.models.order.order_line_item_type import OrderLineItemType
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

    def order_line_items(
        self,
        order: Order,
    ) -> List[OrderLineItem]:
        """
        Returns the OrderLineItems for this OrderGroupMaterial. This method does not
        save the OrderLineItems to the database.
        """
        tons_over_included = (
            self.order_group.tonnage_quantity or 0
        ) - self.order_group.material.tonnage_included

        # Get the OrderLineItemType for MATERIAL.
        order_line_item_type = OrderLineItemType.objects.get(code="MATERIAL")

        order_line_items = []

        # Create OrderLineItem for Included Tons.
        order_line_items.append(
            OrderLineItem(
                order=order,
                order_line_item_type=order_line_item_type,
                rate=self.order_group.material.price_per_ton,
                quantity=self.order_group.material.tonnage_included,
                description="Included Tons",
                platform_fee_percent=self.order_group.take_rate,
            )
        )

        # Create OrderLineItem for Additional Tons.
        if tons_over_included > 0:
            order_line_items.append(
                OrderLineItem(
                    order=order,
                    order_line_item_type=order_line_item_type,
                    rate=self.order_group.material.price_per_ton,
                    quantity=tons_over_included,
                    description="Additional Tons",
                    platform_fee_percent=self.order_group.take_rate,
                )
            )

        return order_line_items
