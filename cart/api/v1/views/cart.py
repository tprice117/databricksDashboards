from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from cart.api.v1.serializers.response.cart import CartSerializer
from cart.utils import CartUtils


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: CartSerializer(),
        },
    )
    def get(self, request):
        """
        Returns:
          A Cart containing a list of CartGroups of CartItems.
        """
        orders = CartUtils.get_booking_objects(request)
        orders = orders.filter(submitted_on__isnull=False).select_related(
            "order_group__seller_product_seller_location__seller_product__seller",
            "order_group__user_address",
            "order_group__user",
            "order_group__seller_product_seller_location__seller_product__product__main_product",
        )
        orders = orders.prefetch_related("payouts", "order_line_items")
        cart_data = CartUtils.get_cart_orders(orders)

        data = CartSerializer(cart_data).data
        return Response(data)
