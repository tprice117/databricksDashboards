from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException
from rest_framework.views import APIView

from pricing_engine.api.v1.serializers import PricingEngineRequestByLatLongSerializer
from pricing_engine.api.v1.serializers.response.pricing_engine_response import (
    PricingEngineResponseSerializer,
)
from pricing_engine.pricing_engine import PricingEngine


class SellerProductSellerLocationPricingByLatLongView(APIView):
    """
    This class-based view returns a list of SellerProductSellerLocations that match the
    given parameters in a POST request.
    """

    @extend_schema(
        request=PricingEngineRequestByLatLongSerializer,
        responses={
            200: PricingEngineResponseSerializer(),
        },
    )
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
        # Convert request into serializer.
        serializer = PricingEngineRequestByLatLongSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise APIException(serializer.errors)

        # Get SellerProductSellerLocations.
        pricing_line_item_groups = PricingEngine.get_price_by_lat_long(
            seller_product_seller_location=serializer.validated_data[
                "seller_product_seller_location"
            ],
            latitude=serializer.validated_data["latitude"],
            longitude=serializer.validated_data["longitude"],
            start_date=serializer.validated_data["start_date"],
            end_date=serializer.validated_data["end_date"],
            waste_type=serializer.validated_data["waste_type"],
            shift_count=serializer.validated_data.get("shift_count"),
        )

        # Return PricingEngineResponse serialized data.
        data = PricingEngineResponseSerializer(
            pricing_line_item_groups,
        ).data

        return JsonResponse(data, safe=False)
