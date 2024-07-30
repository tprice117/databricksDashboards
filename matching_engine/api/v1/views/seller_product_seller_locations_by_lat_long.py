from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import APIException
from rest_framework.views import APIView

from api.serializers import SellerProductSellerLocationSerializer
from matching_engine.api.v1.serializers import MatchingEngineRequestByLatLongSerializer
from matching_engine.matching_engine import MatchingEngine


class GetSellerProductSellerLocationsByLatLongView(APIView):
    """
    This class-based view returns a list of SellerProductSellerLocations that match the
    given parameters in a POST request.
    """

    @extend_schema(
        request=MatchingEngineRequestByLatLongSerializer,
        responses={
            200: SellerProductSellerLocationSerializer(many=True),
        },
    )
    def post(self, request):
        """
        POST Body Args:
          product: Product Id (UUID)
          latitude: User's latitude (Decimal)
          longitude: User's longitude (Decimal)
          waste_type: WasteType Id (UUID or None)

        Returns:
          A list of SellerProductSellerLocations.
        """
        # Convert request into serializer.
        serializer = MatchingEngineRequestByLatLongSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise APIException(serializer.errors)

        # Get SellerProductSellerLocations.
        seller_product_seller_locations = (
            MatchingEngine.get_possible_seller_product_seller_locations_by_lat_long(
                product=serializer.validated_data["product"],
                latitude=serializer.validated_data["latitude"],
                longitude=serializer.validated_data["longitude"],
                waste_type=serializer.validated_data["waste_type"],
            )
        )

        # Return SellerProductSellerLocations serialized data.
        data = SellerProductSellerLocationSerializer(
            seller_product_seller_locations,
            many=True,
        ).data

        return JsonResponse(data, safe=False)
