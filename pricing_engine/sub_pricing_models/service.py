from decimal import Decimal

from api.models.seller.seller_product_seller_location import SellerProductSellerLocation
from api.models.user.user_address import UserAddress
from common.utils.distance.distance import DistanceUtils


class ServicePrice:
    @staticmethod
    def get_price(
        latitude: Decimal,
        longitude: Decimal,
        seller_product_seller_location: SellerProductSellerLocation,
        times_per_week: int = None,
    ):
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
        price = 0
        if (
            seller_product_seller_location.seller_product.product.main_product.has_service
            and seller_product_seller_location.service
        ):
            # Legacy Service Model.
            price = _service_legacy_price(
                seller_product_seller_location=seller_product_seller_location,
                latitude=latitude,
                longitude=longitude,
            )
        elif (
            seller_product_seller_location.seller_product.product.main_product.has_service_times_per_week
            and seller_product_seller_location.service_times_per_week
            and times_per_week
        ):
            # New Times Per Week Service Model.
            price = _service_times_per_week_price(
                seller_product_seller_location=seller_product_seller_location,
                times_per_week=times_per_week,
            )
        if price is None:
            price = 0
        return price


def _service_legacy_price(
    seller_product_seller_location: SellerProductSellerLocation,
    latitude: Decimal,
    longitude: Decimal,
):
    price = 0

    # Legacy Service Model.
    if seller_product_seller_location.service.price_per_mile:
        miles = DistanceUtils.get_euclidean_distance(
            lat1=latitude,
            lon1=longitude,
            lat2=seller_product_seller_location.seller_location.latitude,
            lon2=seller_product_seller_location.seller_location.longitude,
        )

        price += seller_product_seller_location.service.price_per_mile * miles
    if seller_product_seller_location.service.flat_rate_price:
        price += seller_product_seller_location.service.flat_rate_price

    return price


def _service_times_per_week_price(
    seller_product_seller_location: SellerProductSellerLocation,
    times_per_week: int = None,
):
    if (
        seller_product_seller_location.seller_product.product.main_product.has_service_times_per_week
        and seller_product_seller_location.service_times_per_week
        and times_per_week
    ):
        # New Times Per Week Service Model.
        if (
            times_per_week == 1
            and seller_product_seller_location.service_times_per_week.one_time_per_week
        ):
            return (
                seller_product_seller_location.service_times_per_week.one_time_per_week
            )
        elif (
            times_per_week == 2
            and seller_product_seller_location.service_times_per_week.two_times_per_week
        ):
            return (
                seller_product_seller_location.service_times_per_week.two_times_per_week
            )
        elif (
            times_per_week == 3
            and seller_product_seller_location.service_times_per_week.three_times_per_week
        ):
            return (
                seller_product_seller_location.service_times_per_week.three_times_per_week
            )
        elif (
            times_per_week == 4
            and seller_product_seller_location.service_times_per_week.four_times_per_week
        ):
            return (
                seller_product_seller_location.service_times_per_week.four_times_per_week
            )
        elif (
            times_per_week == 5
            and seller_product_seller_location.service_times_per_week.five_times_per_week
        ):
            return (
                seller_product_seller_location.service_times_per_week.five_times_per_week
            )
