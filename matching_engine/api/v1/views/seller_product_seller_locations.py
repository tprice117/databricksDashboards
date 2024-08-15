from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException
from rest_framework.views import APIView

from api.serializers import SellerProductSellerLocationSerializer
from matching_engine.api.v1.serializers import MatchingEngineRequestSerializer
from matching_engine.matching_engine import MatchingEngine
from matching_engine.utils.align_seller_product_seller_location_children_with_main_product import (
    align_seller_product_seller_location_children_with_main_product,
)
from matching_engine.utils.seller_product_seller_location_plus_take_rate import (
    seller_product_seller_location_plus_take_rate,
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

        # Align SellerProductSellerLocations pricing configurations with
        # current MainProduct settings.
        seller_product_seller_locations = [
            align_seller_product_seller_location_children_with_main_product(
                seller_product_seller_location
            )
            for seller_product_seller_location in seller_product_seller_locations
        ]

        # Add default take rate to the price and serialize the data.
        data = []

        for seller_product_seller_location in seller_product_seller_locations:
            data.append(
                seller_product_seller_location_plus_take_rate(
                    seller_product_seller_location,
                )
            )

        return JsonResponse(data, safe=False)
