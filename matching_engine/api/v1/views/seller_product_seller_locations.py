from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.exceptions import APIException
from rest_framework.mixins import CreateModelMixin
from rest_framework.viewsets import GenericViewSet

from api.serializers import SellerProductSellerLocationSerializer
from matching_engine.matching_engine import MatchingEngine


class GetSellerProductSellerLocationsView(GenericViewSet, CreateModelMixin):
    """
    This class-based view returns a list of SellerProductSellerLocations that match the
    given parameters in a POST request.
    """

    serializer_class = SellerProductSellerLocationSerializer

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
