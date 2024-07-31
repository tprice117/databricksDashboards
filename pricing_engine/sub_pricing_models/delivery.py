from typing import Optional

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from pricing_engine.models import PricingLineItem, PricingLineItemGroup


class DeliveryPrice:
    @staticmethod
    def get_price(
        seller_product_seller_location: SellerProductSellerLocation,
    ) -> Optional[PricingLineItemGroup]:
        return (
            PricingLineItemGroup(
                title="Delivery",
                items=[
                    PricingLineItem(
                        description="Delivery Fee",
                        quantity=None,
                        unit_price=seller_product_seller_location.delivery_fee,
                        units=None,
                    )
                ],
            )
            if seller_product_seller_location.delivery_fee
            else None
        )
