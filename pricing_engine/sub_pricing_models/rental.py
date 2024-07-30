import datetime
from typing import Union

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation


class RentalPrice:
    @staticmethod
    def get_price(
        seller_product_seller_location: SellerProductSellerLocation,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> Union[float, None]:
        """
        This method computes the rental price based the SellerProductSellerLocation's
        (and related MainProduct) rental pricing structure.

        Returns:
          The rental price (float)
        """
        if end_date < start_date:
            raise Exception("End Date must be after the Start Date.")

        price = 0

        # Get duration.
        duration = end_date - start_date

        if (
            seller_product_seller_location.seller_product.product.main_product.has_rental_one_step
        ):
            price += seller_product_seller_location.rental_one_step.get_price(
                duration=duration,
            )
        elif (
            seller_product_seller_location.seller_product.product.main_product.has_rental
        ):
            price += seller_product_seller_location.rental.get_price(
                duration=duration,
            )
        elif (
            seller_product_seller_location.seller_product.product.main_product.has_rental_multi_step
        ):
            price += seller_product_seller_location.rental_multi_step.get_price(
                duration=duration,
            )

        return price
