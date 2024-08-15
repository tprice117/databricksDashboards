from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException
from rest_framework.views import APIView

from api.models.main_product.product import Product
from api.serializers import SellerProductSellerLocationSerializer
from matching_engine.api.v1.serializers import MatchingEngineRequestSerializer
from matching_engine.matching_engine import MatchingEngine
from matching_engine.utils.prep_seller_product_seller_locations_for_response import (
    prep_seller_product_seller_locations_for_response,
)


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
        # Convert request into serializer.
        serializer = MatchingEngineRequestSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise APIException(serializer.errors)

        # Get SellerProductSellerLocations.
        seller_product_seller_locations = (
            MatchingEngine.get_possible_seller_product_seller_locations(
                product=serializer.validated_data["product"],
                user_address=serializer.validated_data["user_address"],
                waste_type=serializer.validated_data["waste_type"],
            )
        )

        # Get typed Product object.
        product: Product = serializer.validated_data["product"]

        # Get response data.
        data = prep_seller_product_seller_locations_for_response(
            main_product=product.main_product,
            seller_product_seller_locations=seller_product_seller_locations,
        )

        return JsonResponse(data, safe=False)
