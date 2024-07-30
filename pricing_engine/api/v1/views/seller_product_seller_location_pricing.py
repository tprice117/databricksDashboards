import datetime

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException
from rest_framework.views import APIView

from api.serializers import SellerProductSellerLocationSerializer
from pricing_engine.api.v1.serializers import PricingEngineRequestSerializer
from pricing_engine.pricing_engine import PricingEngine


class SellerProductSellerLocationPricingView(APIView):
    """
    This class-based view returns a list of SellerProductSellerLocations that match the
    given parameters in a POST request.
    """

    @extend_schema(
        request=PricingEngineRequestSerializer,
        responses={
            200: SellerProductSellerLocationSerializer(many=True),
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
        serializer = PricingEngineRequestSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise APIException(serializer.errors)

        # Get SellerProductSellerLocations.
        seller_product_seller_locations = PricingEngine.get_price(
            seller_product_seller_location=serializer.validated_data[
                "seller_product_seller_location"
            ],
            user_address=serializer.validated_data["user_address"],
            start_date=serializer.validated_data["start_date"],
            end_date=serializer.validated_data["end_date"],
            waste_type=serializer.validated_data["waste_type"],
        )

        # Return SellerProductSellerLocations serialized data.
        data = SellerProductSellerLocationSerializer(
            seller_product_seller_locations,
            many=True,
        ).data

        return JsonResponse(data, safe=False)
