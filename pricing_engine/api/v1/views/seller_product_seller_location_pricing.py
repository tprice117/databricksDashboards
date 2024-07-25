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
        # Get POST body args.
        try:
            seller_product_seller_location = request.data.get(
                "seller_product_seller_location"
            )
            user_address = request.data.get("user_address")
            waste_type = request.data.get("waste_type")
            start_date = request.data.get("start_date")
            end_date = request.data.get("end_date")
        except KeyError as e:
            raise APIException(f"Missing required field: {e.args[0]}") from e

        # Convert start_date and end_date to datetime objects.
        start_date = datetime.datetime.fromisoformat(start_date)
        end_date = datetime.datetime.fromisoformat(end_date)

        # Get SellerProductSellerLocations.
        seller_product_seller_locations = PricingEngine.get_price(
            seller_product_seller_location=seller_product_seller_location,
            user_address=user_address,
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
