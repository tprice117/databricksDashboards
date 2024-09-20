from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import (
    APIException,
    ValidationError as DRFValidationError,
)
from rest_framework.views import APIView

from cart.api.v1.serializers import (
    CheckoutRequestSerializer,
    CheckoutResponseSerializer,
)
from cart.utils import CheckoutUtils
from cart.models import CheckoutOrder
from common.utils.json_encoders import DecimalFloatEncoder


class CheckoutView(APIView):
    """
    This class-based view returns a CheckoutOrder if the checkout was successful.
    """

    @extend_schema(
        request=CheckoutRequestSerializer,
        responses={
            201: CheckoutResponseSerializer(),
        },
    )
    def post(self, request):
        """
        POST Body Args:
          user_address: UserAddress Id (UUID)
          payment_method: PaymentMethod Id (UUID or None) If None, then api assumes Pay Later is True.

        Returns:
          A CheckoutOrder.
        """
        # Convert request into serializer.
        serializer = CheckoutRequestSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise APIException(serializer.errors)

        # Get cart from address.
        user_address = serializer.validated_data["user_address"]
        cart_orders = user_address.get_cart()

        payment_method_id = serializer.validated_data.get("payment_method", None)

        # If payment_method is None, then assume pay_later is True.
        user_group = serializer.validated_data["user_address"].user_group
        if not payment_method_id:
            if user_group is None:
                raise DRFValidationError(
                    detail="Payment method is required. User is not part of a company."
                )

            if not user_group.credit_limit_remaining:
                raise DRFValidationError(
                    detail="Payment method is required. Company does not have credit terms."
                )

        checkout_order = CheckoutUtils.checkout(
            user_address, cart_orders, payment_method_id
        )

        # Return CheckoutOrder serialized data.
        data = CheckoutResponseSerializer(
            checkout_order,
        ).data

        return JsonResponse(data, encoder=DecimalFloatEncoder, safe=False)

    @extend_schema(
        responses={
            200: CheckoutResponseSerializer(),
        },
    )
    def get(self, request):
        """
        Returns:
          A list of CheckoutOrders.
        """
        checkout_orders = CheckoutOrder.objects.filter(
            user_address__user_group=request.user.user_group
        )
        # checkout_orders = CheckoutUtils.get_all_checkout_orders()

        # Return CheckoutOrder serialized data.
        data = CheckoutResponseSerializer(
            checkout_orders,
            many=True,
        ).data

        return JsonResponse(data, encoder=DecimalFloatEncoder, safe=False)
