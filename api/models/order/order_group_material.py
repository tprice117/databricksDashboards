from typing import List

from django.db import models

from api.models.common.material import PricingMaterial
from api.models.order.order import Order
from api.models.order.order_line_item import OrderLineItem
from api.models.order.order_line_item_type import OrderLineItemType


class OrderGroupMaterial(PricingMaterial):
    order_group = models.OneToOneField(
        "api.OrderGroup",
        on_delete=models.CASCADE,
        related_name="material",
    )
    price_per_ton = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        help_text="Deprecated. Use OrderGroupMaterialWasteType(s) instead of this field.",
    )
    tonnage_included = models.IntegerField(
        default=0,
        help_text="Deprecated. Use OrderGroupMaterialWasteType(s) instead of this field.",
    )

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
        # Get the OrderLineItemType for MATERIAL.
        order_line_item_type = OrderLineItemType.objects.get(code="MATERIAL")

        line_item = self.get_price(
            waste_type=self.order_group.waste_type,
            tons=self.order_group.tonnage_quantity,
        )

        return [
            OrderLineItem(
                order=order,
                order_line_item_type=order_line_item_type,
                rate=line_item.unit_price,
                quantity=line_item.quantity,
                description=line_item.description,
                platform_fee_percent=self.order_group.take_rate,
            )
        ]
