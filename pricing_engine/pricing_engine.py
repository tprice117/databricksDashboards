import datetime
from typing import Optional

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from api.models.user.user_address import UserAddress
from api.models.waste_type import WasteType
from pricing_engine.sub_pricing_models import MaterialPrice, RentalPrice, ServicePrice


class PricingEngine:
    @staticmethod
    def get_price(
        user_address: UserAddress,
        seller_product_seller_location: SellerProductSellerLocation,
        start_date: datetime.datetime,
        end_date: Optional[datetime.datetime],
        waste_type: Optional[WasteType],
    ):
        """
        This method calls the sub-classes to compute the total price based on
        customer location, seller location, and product.

        Args:
          customer_location: Customer's location (string)
          seller_location: Seller's location (string)
          product: Product type (string)

        Returns:
          A dictionary containing the total price broken down into service, rental,
          and material costs.
        """
        # Ensure the SellerProductSellerLocation is completely configured.
        if not seller_product_seller_location.is_complete:
            return None

        # Service price.
        service = ServicePrice.get_price(
            user_address=user_address,
            seller_product_seller_location=seller_product_seller_location,
        )

        # Rental
        rental = RentalPrice.get_price(
            seller_product_seller_location,
            start_date=start_date,
            end_date=end_date,
        )

        # Material.
        material = (
            MaterialPrice.get_price(
                seller_product_seller_location,
                waste_type=waste_type,
            )
            if waste_type
            else 0
        )

        return {
            "service": service,
            "rental": rental,
            "material": material,
            "total": service + rental + material,
            "delivery": PricingEngine.get_delivery_price(
                user_address=user_address,
                seller_product_seller_location=seller_product_seller_location,
            ),
            "removal": PricingEngine.get_removal_price(
                user_address=user_address,
                seller_product_seller_location=seller_product_seller_location,
            ),
        }

    @staticmethod
    def get_delivery_price(
        user_address: UserAddress,
        seller_product_seller_location: SellerProductSellerLocation,
    ):
        return seller_product_seller_location.delivery_fee

    @staticmethod
    def get_removal_price(
        user_address: UserAddress,
        seller_product_seller_location: SellerProductSellerLocation,
    ):
        return seller_product_seller_location.removal_fee
