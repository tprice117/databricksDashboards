import datetime
from decimal import Decimal
import logging
from typing import List, Optional, Tuple

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

logger = logging.getLogger(__name__)


class PricingEngine:
    @staticmethod
    def get_price(
        user_address: UserAddress,
        seller_product_seller_location,  # SellerProductSellerLocation
        start_date: datetime.date,
        end_date: datetime.date,
        waste_type: Optional[WasteType],
        shift_count: Optional[int],
        times_per_week: Decimal = None,
        discount: Optional[Decimal] = None,
    ) -> List[Tuple[PricingLineItemGroup, List[PricingLineItem]]]:
        return PricingEngine.get_price_by_lat_long(
            latitude=user_address.latitude,
            longitude=user_address.longitude,
            seller_product_seller_location=seller_product_seller_location,
            start_date=start_date,
            end_date=end_date,
            waste_type=waste_type,
            shift_count=shift_count,
            times_per_week=times_per_week,
            discount=discount,
        )

    @staticmethod
    def get_price_by_lat_long(
        latitude: Decimal,
        longitude: Decimal,
        seller_product_seller_location,  # SellerProductSellerLocation
        start_date: datetime.date,
        end_date: Optional[datetime.date],
        waste_type: Optional[WasteType],
        shift_count: Optional[int],
        times_per_week: Optional[Decimal] = None,
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
            # Convert the discount to a percentage since discount is in that format 0-100
            max_discount_100 = (
                seller_product_seller_location.seller_product.product.main_product.max_discount
                * 100
            )
            if discount > max_discount_100:
                raise Exception(
                    "Discount cannot be greater than "
                    f"{seller_product_seller_location.seller_product.product.main_product.max_discount}"
                    " for this product."
                )

        # Validate the times_per_week parameter.
        # If the product does not support times_per_week, but the parameter is passed,
        # give a warning and set times_per_week to None.
        # If the product supports times_per_week, but the parameter is not passed,
        # raise an exception.
        if (
            not seller_product_seller_location.seller_product.product.main_product.has_service_times_per_week
            and times_per_week is not None
        ):
            logger.warning(
                f"{seller_product_seller_location.seller_product.product.main_product} does not support times_per_week. Please remove this parameter."
            )
            times_per_week = None
        if (
            seller_product_seller_location.seller_product.product.main_product.has_service_times_per_week
            and times_per_week is None
        ):
            raise Exception(
                "This product requires times_per_week. Please include this parameter."
            )

        response = {}

        # Service price.
        service = ServicePrice.get_price(
            latitude=latitude,
            longitude=longitude,
            seller_product_seller_location=seller_product_seller_location,
            times_per_week=times_per_week,
        )
        if service:
            service[0].sort = 0

        # Rental
        rental = RentalPrice.get_price(
            seller_product_seller_location,
            start_date=start_date,
            end_date=end_date,
            shift_count=shift_count,
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

        # Begin constructing the response.
        response: List[Tuple[PricingLineItemGroup, List[PricingLineItem]]]
        response = [
            service,
            rental,
            material,
            delivery,
            removal,
        ]

        # Filter out None values.
        response = [x for x in response if x]

        # Fuel and environmental Fees.
        subtotal = sum(
            [
                sum(
                    [
                        float(x.unit_price) * float(x.quantity)
                        for x in group_and_items[1]
                    ]
                )
                for group_and_items in response
                if group_and_items and group_and_items[1] is not None
            ]
        )
        fuel_and_environmental = FuelAndEnvironmentalPrice.get_price(
            seller_product_seller_location=seller_product_seller_location,
            subtotal=subtotal,
        )
        if fuel_and_environmental:
            fuel_and_environmental[0].sort = 5

        # Append the fuel and environmental fees to the response.
        if fuel_and_environmental:
            response.append(fuel_and_environmental)

        # For each item in the response, add the take rate to the unit price.
        effective_take_rate = seller_product_seller_location.seller_product.product.main_product.default_take_rate

        for _, items in response:
            for item in items:
                price_with_take_rate = float(item.unit_price) * (
                    1 + float(effective_take_rate / 100)
                )
                price_after_discount = (
                    price_with_take_rate * (1 - float(discount / 100))
                    if discount
                    else price_with_take_rate
                )
                item.unit_price = price_after_discount

        # Sort the response.
        response = sorted(
            response,
            key=lambda x: x[0].sort,
        )

        return response
