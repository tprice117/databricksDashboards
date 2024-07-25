from django.http import JsonResponse
from django.views.generic import View
from rest_framework.exceptions import APIException

from api.serializers import SellerProductSellerLocationSerializer
from matching_engine.utils.matching_engine.matching_engine import MatchingEngine
from pricing_engine.pricing_engine import PricingEngine


class SellerProductSellerLocationPricingView(View):
    """
    This class-based view returns a list of SellerProductSellerLocations that match the
    given parameters in a POST request.
    """

    http_method_names = ["post"]  # Only accept POST requests

    def post(self, request, *args, **kwargs):
        """
        POST Body Args:
          seller_product_seller_location: SellerProductSellerLocation Id (UUID)
          user_address: User's address (string)
          waste_type: Waste type (string or None)

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
        except KeyError as e:
            raise APIException(f"Missing required field: {e.args[0]}") from e

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
