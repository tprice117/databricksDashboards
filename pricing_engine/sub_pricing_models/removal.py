from typing import Optional, Tuple, Union

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from pricing_engine.models import PricingLineItem, PricingLineItemGroup


class RemovalPrice:
    @staticmethod
    def get_price(
        seller_product_seller_location: SellerProductSellerLocation,
    ) -> Optional[Union[Tuple[PricingLineItemGroup, list[PricingLineItem]], None]]:

        item = PricingLineItem(
            description="Removal Fee",
            unit_price=seller_product_seller_location.removal_fee,
            units=None,
        )

        return (
            (
                PricingLineItemGroup(
                    title="Removal",
                    code="material",
                ),
                [item],
            )
            if seller_product_seller_location.removal_fee
            else None
        )
