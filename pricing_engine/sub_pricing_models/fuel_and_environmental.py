from typing import Optional, Tuple, Union

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from pricing_engine.models import PricingLineItem, PricingLineItemGroup


class FuelAndEnvironmentalPrice:
    @staticmethod
    def get_price(
        seller_product_seller_location: SellerProductSellerLocation,
        subtotal: float,
    ) -> Optional[Union[Tuple[PricingLineItemGroup, list[PricingLineItem]], None]]:
        return (
            (
                PricingLineItemGroup(
                    title="Fuel and Environmental",
                    code="fuel_and_environmental",
                ),
                [
                    PricingLineItem(
                        description=None,
                        unit_price=seller_product_seller_location.fuel_environmental_markup
                        * subtotal,
                        units=None,
                    )
                ],
            )
            if seller_product_seller_location.fuel_environmental_markup
            else None
        )
