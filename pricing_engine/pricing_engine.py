import datetime
from decimal import Decimal
from typing import Optional

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from api.models.user.user_address import UserAddress
from api.models.waste_type import WasteType
from pricing_engine.models import PricingLineItemGroup
from pricing_engine.serializers.pricing_line_item import PricingLineItemSerializer
from pricing_engine.serializers.pricing_line_item_group import (
    PricingLineItemGroupSerializer,
)
from pricing_engine.sub_pricing_models import MaterialPrice, RentalPrice, ServicePrice
from pricing_engine.sub_pricing_models.delivery import DeliveryPrice
from pricing_engine.sub_pricing_models.removal import RemovalPrice


class PricingEngine:
    @staticmethod
    def get_price(
        user_address: UserAddress,
        seller_product_seller_location: SellerProductSellerLocation,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        waste_type: Optional[WasteType],
    ) -> dict:
        return PricingEngine.get_price_by_lat_long(
            latitude=user_address.latitude,
            longitude=user_address.longitude,
            seller_product_seller_location=seller_product_seller_location,
            start_date=start_date,
            end_date=end_date,
            waste_type=waste_type,
        )

    @staticmethod
    def get_price_by_lat_long(
        latitude: Decimal,
        longitude: Decimal,
        seller_product_seller_location: SellerProductSellerLocation,
        start_date: datetime.datetime,
        end_date: Optional[datetime.datetime],
        waste_type: Optional[WasteType],
    ) -> dict:
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

        response = {}

        # Service price.
        service = ServicePrice.get_price(
            latitude=latitude,
            longitude=longitude,
            seller_product_seller_location=seller_product_seller_location,
        )
        if service:
            response["service"] = PricingLineItemGroupSerializer(service[0]).data
            response["service"]["items"] = PricingLineItemSerializer(
                service[1],
                many=True,
            ).data
        else:
            response["service"] = None

        # Rental
        rental = RentalPrice.get_price(
            seller_product_seller_location,
            start_date=start_date,
            end_date=end_date,
        )
        if rental:
            response["rental"] = PricingLineItemGroupSerializer(rental[0]).data
            response["rental"]["items"] = PricingLineItemSerializer(
                rental[1],
                many=True,
            ).data
        else:
            response["rental"] = None

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
            response["material"] = PricingLineItemGroupSerializer(material[0]).data
            response["material"]["items"] = PricingLineItemSerializer(
                material[1],
                many=True,
            ).data
        else:
            response["material"] = None

        # Delivery.
        delivery = DeliveryPrice.get_price(
            seller_product_seller_location=seller_product_seller_location,
        )
        if delivery:
            response["delivery"] = PricingLineItemGroupSerializer(delivery[0]).data
            response["delivery"]["items"] = PricingLineItemSerializer(
                delivery[1],
                many=True,
            ).data
        else:
            response["delivery"] = None

        # Removal.
        removal = RemovalPrice.get_price(
            seller_product_seller_location=seller_product_seller_location,
        )
        if removal:
            response["removal"] = PricingLineItemGroupSerializer(removal[0]).data
            response["removal"]["items"] = PricingLineItemSerializer(
                removal[1],
                many=True,
            ).data
        else:
            response["removal"] = None

        print(
            {
                "total": sum(
                    [
                        sum([item.unit_price for item in service[1]]) if service else 0,
                        sum([item.unit_price for item in rental[1]]) if rental else 0,
                        (
                            sum([item.unit_price for item in material[1]])
                            if material
                            else 0
                        ),
                        (
                            sum([item.unit_price for item in delivery[1]])
                            if delivery
                            else 0
                        ),
                        sum([item.unit_price for item in removal[1]]) if removal else 0,
                    ]
                )
            }
            | response
        )

        return {
            "total": sum(
                [
                    sum([item.unit_price for item in service[1]]) if service else 0,
                    sum([item.unit_price for item in rental[1]]) if rental else 0,
                    sum([item.unit_price for item in material[1]]) if material else 0,
                    sum([item.unit_price for item in delivery[1]]) if delivery else 0,
                    sum([item.unit_price for item in removal[1]]) if removal else 0,
                ]
            )
        } | response
