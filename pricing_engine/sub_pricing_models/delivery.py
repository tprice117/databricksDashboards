from typing import Optional, Tuple, Union

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from pricing_engine.models import PricingLineItem, PricingLineItemGroup


class DeliveryPrice:
    @staticmethod
    def get_price(
        seller_product_seller_location: SellerProductSellerLocation,
    ) -> Optional[Union[Tuple[PricingLineItemGroup, list[PricingLineItem]], None]]:
        return (
            (
                PricingLineItemGroup(
                    title="Delivery",
                ),
                [
                    PricingLineItem(
                        description="Delivery Fee",
                        unit_price=seller_product_seller_location.delivery_fee,
                        units=None,
                    )
                ],
            )
            if seller_product_seller_location.delivery_fee
            else None
        )
