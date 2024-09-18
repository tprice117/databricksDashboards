from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException
from rest_framework.views import APIView

from pricing_engine.api.v1.serializers import (
    PricingEngineRequestByUserAddressSerializer,
)
from pricing_engine.api.v1.serializers.response.pricing_engine_response import (
    PricingEngineResponseSerializer,
)
from pricing_engine.pricing_engine import PricingEngine
from common.utils.json_encoders import DecimalFloatEncoder


class SellerProductSellerLocationPricingView(APIView):
    """
    This class-based view returns a list of SellerProductSellerLocations that match the
    given parameters in a POST request.
    """

    @extend_schema(
        request=PricingEngineRequestByUserAddressSerializer,
        responses={
            200: PricingEngineResponseSerializer(),
        },
    )
    def post(self, request):
        """
        POST Body Args:
          seller_product_seller_location: SellerProductSellerLocation Id (UUID)
          user_address: User's address (string)
          waste_type: Waste type (string or None)
          start_date: Start date (datetime in ISO format)
          end_date: End date (datetime in ISO format)

        Returns:
          A list of SellerProductSellerLocations.
        """
        # Convert request into serializer.
        serializer = PricingEngineRequestByUserAddressSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise APIException(serializer.errors)

        # Get SellerProductSellerLocations.
        pricing_line_item_groups = PricingEngine.get_price(
            seller_product_seller_location=serializer.validated_data[
                "seller_product_seller_location"
            ],
            user_address=serializer.validated_data.get("user_address"),
            start_date=serializer.validated_data.get("start_date"),
            end_date=serializer.validated_data.get("end_date"),
            waste_type=serializer.validated_data.get("waste_type"),
            times_per_week=serializer.validated_data.get("times_per_week"),
            shift_count=serializer.validated_data.get("shift_count"),
        )

        # Return SellerProductSellerLocations serialized data.
        data = PricingEngineResponseSerializer(
            pricing_line_item_groups,
        ).data

        return JsonResponse(data, encoder=DecimalFloatEncoder, safe=False)
