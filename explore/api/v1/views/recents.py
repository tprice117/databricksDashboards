from django.db.models import Max
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView

from api.models import MainProduct, OrderGroup
from api.serializers import (
    MainProductSerializer,
)
from common.utils.pagination import CustomLimitOffsetPagination


# Explore page
class RecentsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MainProductSerializer
    pagination_class = CustomLimitOffsetPagination

    @extend_schema(
        responses={
            200: MainProductSerializer(many=True),
        },
    )
    def get_queryset(self):
        """Gets the most recently ordered products from the request User."""
        # Get the most recent orders for the user (staff gets all orders)
        most_recent_orders = (
            OrderGroup.objects.filter(user=self.request.user).distinct()
            if not self.request.user.is_staff
            else OrderGroup.objects.all()
        )

        # Get the most recent orders, grouping by main product
        most_recent_orders = (
            most_recent_orders.filter(agreement_signed_on__isnull=False)
            .values(
                "seller_product_seller_location__seller_product__product__main_product",
            )
            .annotate(latest_date=Max("created_on"))
            .order_by("-latest_date")
        )

        # A list of unique main product ids, ordered from most recent to least recent
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

        return main_products
