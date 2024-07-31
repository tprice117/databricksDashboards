from typing import Optional

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from pricing_engine.models import PricingLineItem, PricingLineItemGroup


class RemovalPrice:
    @staticmethod
    def get_price(
        seller_product_seller_location: SellerProductSellerLocation,
    ) -> Optional[PricingLineItemGroup]:
        return (
            PricingLineItemGroup(
                title="Removal",
                items=[
                    PricingLineItem(
                        description="Removal Fee",
                        quantity=None,
                        unit_price=seller_product_seller_location.removal_fee,
                        units=None,
                    )
                ],
            )
            if seller_product_seller_location.removal_fee
            else None
        )
