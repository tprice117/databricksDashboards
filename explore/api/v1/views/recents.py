from django.db.models import Max
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from api.models import MainProduct, OrderGroup
from explore.api.v1.serializers import (
    ExploreMainProductSerializer,
)


# Explore page
class RecentsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: ExploreMainProductSerializer(),
        },
    )
    def get(self, request):
        """Gets the 5 most recently ordered products from the request User."""
        # Get the most recent orders for the user (staff gets all orders)
        most_recent_orders = (
            OrderGroup.objects.filter(user=request.user).distinct()
            if not request.user.is_staff
            else OrderGroup.objects.all()
        )

        # Get the 5 most recent orders, grouping by main product
        most_recent_orders = (
            most_recent_orders.values(
                "seller_product_seller_location__seller_product__product__main_product",
            )
            .annotate(latest_date=Max("created_on"))
            .order_by("-latest_date")[:5]
        )

        # A list of at most 5 unique main product ids, ordered from most recent to least recent
        main_product_ids = [
            ordergroup[
                "seller_product_seller_location__seller_product__product__main_product"
            ]
            for ordergroup in most_recent_orders
        ]

        # Fetch main product objects while preserving the order of main_product_ids
        preserved_order = {id: index for index, id in enumerate(main_product_ids)}
        main_products = MainProduct.objects.filter(id__in=main_product_ids)
        main_products = sorted(main_products, key=lambda x: preserved_order[x.id])

        # Serialize the main products
        data = ExploreMainProductSerializer(
            main_products,
            many=True,
        ).data
        return Response(data)
