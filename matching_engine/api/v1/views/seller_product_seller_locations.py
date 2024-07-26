from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException
from rest_framework.views import APIView

from api.serializers import SellerProductSellerLocationSerializer
from matching_engine.api.v1.serializers import MatchingEngineRequestSerializer
from matching_engine.matching_engine import MatchingEngine


class GetSellerProductSellerLocationsView(APIView):
    """
    This class-based view returns a list of SellerProductSellerLocations that match the
    given parameters in a POST request.
    """

    @extend_schema(
        request=MatchingEngineRequestSerializer,
        responses={
            200: SellerProductSellerLocationSerializer(many=True),
        },
    )
    def post(self, request):
        """
        POST Body Args:
          product: Product Id (UUID)
          user_address: UserAddress Id (UUID)
          waste_type: WasteType Id (UUID or None)

        Returns:
          A list of SellerProductSellerLocations.
        """
        # Get POST body args.
        try:
            product = request.data.get("product")
            user_address = request.data.get("user_address")
            waste_type = request.data.get("waste_type")
        except KeyError as e:
            raise APIException(f"Missing required field: {e.args[0]}") from e

        # Get SellerProductSellerLocations.
        seller_product_seller_locations = (
            MatchingEngine.get_possible_seller_product_seller_locations(
                product=product,
                user_address=user_address,
                waste_type=waste_type,
            )
        )

        # Return SellerProductSellerLocations serialized data.
        data = SellerProductSellerLocationSerializer(
            seller_product_seller_locations,
            many=True,
        ).data

        return JsonResponse(data, safe=False)
