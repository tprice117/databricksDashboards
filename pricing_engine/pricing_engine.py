import datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from api.models.user.user_address import UserAddress
from api.models.waste_type import WasteType
from pricing_engine.models import PricingLineItemGroup
from pricing_engine.models.pricing_line_item import PricingLineItem
from pricing_engine.sub_pricing_models import MaterialPrice, RentalPrice, ServicePrice
from pricing_engine.sub_pricing_models.delivery import DeliveryPrice
from pricing_engine.sub_pricing_models.fuel_and_environmental import (
    FuelAndEnvironmentalPrice,
)
from pricing_engine.sub_pricing_models.removal import RemovalPrice


class PricingEngine:
    @staticmethod
    def get_price(
        user_address: UserAddress,
        seller_product_seller_location: SellerProductSellerLocation,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        waste_type: Optional[WasteType],
        discount: Optional[Decimal] = None,
    ) -> List[Tuple[PricingLineItemGroup, List[PricingLineItem]]]:
        return PricingEngine.get_price_by_lat_long(
            latitude=user_address.latitude,
            longitude=user_address.longitude,
            seller_product_seller_location=seller_product_seller_location,
            start_date=start_date,
            end_date=end_date,
            waste_type=waste_type,
            discount=discount,
        )

    @staticmethod
    def get_price_by_lat_long(
        latitude: Decimal,
        longitude: Decimal,
        seller_product_seller_location: SellerProductSellerLocation,
        start_date: datetime.datetime,
        end_date: Optional[datetime.datetime],
        waste_type: Optional[WasteType],
        discount: Optional[Decimal] = None,
    ) -> List[Tuple[PricingLineItemGroup, List[PricingLineItem]]]:
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

        # If discount is passed, ensure that it is not greater than
        # the difference between the MainProduct default_take_rate and the
        # minimum_take_rate.
        if discount:
            if (
                discount
                > seller_product_seller_location.seller_product.product.main_product.max_discount
            ):
                return Exception(
                    "Discount cannot be greater than "
                    f"{seller_product_seller_location.seller_product.product.main_product.max_discount}"
                    " for this product."
                )

        response = {}

        # Service price.
        service = ServicePrice.get_price(
            latitude=latitude,
            longitude=longitude,
            seller_product_seller_location=seller_product_seller_location,
        )
        if service:
            service[0].sort = 0

        # Rental
        rental = RentalPrice.get_price(
            seller_product_seller_location,
            start_date=start_date,
            end_date=end_date,
        )
        if rental:
            rental[0].sort = 1

        # Material.
        material = (
            MaterialPrice.get_price(
                seller_product_seller_location,
                waste_type=waste_type,
            )
            if waste_type
            else 0
        )
        if material:
            material[0].sort = 2

        # Delivery.
        delivery = DeliveryPrice.get_price(
            seller_product_seller_location=seller_product_seller_location,
        )
        if delivery:
            delivery[0].sort = 3

        # Removal.
        removal = RemovalPrice.get_price(
            seller_product_seller_location=seller_product_seller_location,
        )
        if removal:
            removal[0].sort = 4

        # Fuel and environmental Fees.
        subtotal = sum(
            [
                sum(
                    [
                        float(x.unit_price) * float(x.quantity)
                        for x in group_and_items[1]
                    ]
                )
                for group_and_items in [service, rental, material, delivery, removal]
                if group_and_items and group_and_items[1] is not None
            ]
        )
        fuel_and_environmental_fees = FuelAndEnvironmentalPrice.get_price(
            seller_product_seller_location=seller_product_seller_location,
            subtotal=subtotal,
        )
        if fuel_and_environmental_fees:
            fuel_and_environmental_fees[0].sort = 5

        # Construct the response.
        response: List[Tuple[PricingLineItemGroup, List[PricingLineItem]]]
        response = [
            service,
            rental,
            material,
            delivery,
            removal,
            fuel_and_environmental_fees,
        ]

        # For each item in the response, add the take rate to the unit price.
        effective_take_rate = (
            seller_product_seller_location.seller_product.product.main_product.default_take_rate
        )
        for _, items in response:
            for item in items:
                price_with_take_rate = item.unit_price * (1 + effective_take_rate)
                price_after_discount = (
                    price_with_take_rate * (1 - discount)
                    if discount
                    else price_with_take_rate
                )
                item.unit_price = price_after_discount

        # Filter out None values.
        response = [x for x in response if x]

        # Sort the response.
        response = sorted(
            response,
            key=lambda x: x[0].sort,
        )

        return response
