import datetime
from typing import Optional, Tuple, Union

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from pricing_engine.models import PricingLineItem, PricingLineItemGroup


class RentalPrice:
    @staticmethod
    def get_price(
        seller_product_seller_location: SellerProductSellerLocation,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> Optional[Union[Tuple[PricingLineItemGroup, list[PricingLineItem]], None]]:
        """
        This method computes the rental price based the SellerProductSellerLocation's
        (and related MainProduct) rental pricing structure.

        Returns:
          The rental price (float)
        """
        if end_date < start_date:
            raise Exception("End Date must be after the Start Date.")

        # Create empty list of PricingLineItems.
        items: list[PricingLineItem] = []

        # Get duration.
        duration = end_date - start_date

        if (
            seller_product_seller_location.seller_product.product.main_product.has_rental_one_step
        ):
            items.append(
                seller_product_seller_location.rental_one_step.get_price(
                    duration=duration,
                )
            )
        elif (
            seller_product_seller_location.seller_product.product.main_product.has_rental
        ):
            items.extend(
                seller_product_seller_location.rental.get_price(
                    duration=duration,
                )
            )
        elif (
            seller_product_seller_location.seller_product.product.main_product.has_rental_multi_step
        ):
            items.extend(
                seller_product_seller_location.rental_multi_step.get_price(
                    duration=duration,
                )
            )

        return (
            (
                PricingLineItemGroup(
                    title="Rental",
                    code="rental",
                ),
                items,
            )
            if len(items) > 0
            else None
        )
