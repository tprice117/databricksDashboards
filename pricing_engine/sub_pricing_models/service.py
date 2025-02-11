from decimal import Decimal
from typing import Optional, Tuple, Union

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from api.models.user.user_address import UserAddress
from common.utils.distance.distance import DistanceUtils
from pricing_engine.models import PricingLineItem, PricingLineItemGroup


class ServicePrice:
    @staticmethod
    def get_price(
        latitude: Decimal,
        longitude: Decimal,
        seller_product_seller_location: SellerProductSellerLocation,
        times_per_week: Optional[Decimal] = None,
    ) -> Optional[Union[Tuple[PricingLineItemGroup, list[PricingLineItem]], None]]:
        """
        This method computes the service price based on customer location,
        seller location, and product. You'll need to implement the logic here
        considering factors like distance, product complexity, etc.

        Args:
          latitude: The customer's latitude (float)
          longitude: The customer's longitude (float)
          seller_product_seller_location: SellerProductSellerLocation object
          times_per_week [Optional]: Number of times per week the service is required (int)

        Returns:
          The service price (float)
        """
        group = PricingLineItemGroup(
            title="Service",
            code="service",
        )

        if (
            seller_product_seller_location.seller_product.product.main_product.has_service
            and hasattr(seller_product_seller_location, "service")
        ):
            # Legacy Service Model.
            miles = DistanceUtils.get_euclidean_distance(
                lat1=latitude,
                lon1=longitude,
                lat2=seller_product_seller_location.seller_location.latitude,
                lon2=seller_product_seller_location.seller_location.longitude,
            )

            items = seller_product_seller_location.service.get_price(
                miles=miles,
            )

            return (
                group,
                items,
            )
        elif (
            seller_product_seller_location.seller_product.product.main_product.has_service_times_per_week
            and hasattr(seller_product_seller_location, "service_times_per_week")
            and times_per_week
        ):
            # New Times Per Week Service Model.
            item = seller_product_seller_location.service_times_per_week.get_price(
                times_per_week=times_per_week,
            )

            return (
                group,
                [item],
            )
