import datetime

from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.exceptions import APIException
from rest_framework.mixins import CreateModelMixin
from rest_framework.viewsets import GenericViewSet

from api.serializers import SellerProductSellerLocationSerializer
from pricing_engine.pricing_engine import PricingEngine


class SellerProductSellerLocationPricingByLatLongView(GenericViewSet, CreateModelMixin):
    """
    This class-based view returns a list of SellerProductSellerLocations that match the
    given parameters in a POST request.
    """

    def post(self, request):
        """
        POST Body Args:
          seller_product_seller_location: SellerProductSellerLocation Id (UUID)
          latitude: User's latitude (Decimal)
          longitude: User's longitude (Decimal)
          waste_type: Waste type (string or None)
          start_date: Start date (datetime in ISO format)
          end_date: End date (datetime in ISO format)

        Returns:
          A list of SellerProductSellerLocations.
        """
        # Get POST body args.
        try:
            seller_product_seller_location = request.data.get(
                "seller_product_seller_location"
            )
            latitude = request.data.get("latitude")
            longitude = request.data.get("longitude")
            waste_type = request.data.get("waste_type")
            start_date = request.data.get("start_date")
            end_date = request.data.get("end_date")
        except KeyError as e:
            raise APIException(f"Missing required field: {e.args[0]}") from e

        # Convert start_date and end_date to datetime objects.
        start_date = datetime.datetime.fromisoformat(start_date)
        end_date = datetime.datetime.fromisoformat(end_date)

        # Get SellerProductSellerLocations.
        seller_product_seller_locations = PricingEngine.get_price_by_lat_long(
            seller_product_seller_location=seller_product_seller_location,
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=start_date,
            waste_type=waste_type,
        )

        # Return SellerProductSellerLocations serialized data.
        data = SellerProductSellerLocationSerializer(
            seller_product_seller_locations,
            many=True,
        ).data

        return JsonResponse(data, safe=False)
