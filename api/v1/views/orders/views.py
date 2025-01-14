from drf_spectacular.utils import extend_schema, OpenApiTypes
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import (
    APIException,
    ValidationError as DRFValidationError,
)
from django_filters import rest_framework as filters

from api.serializers import OrderSerializer
from api.models import Order
from api.filters import OrderFilterset
from cart.utils import CartUtils


class OrderViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = OrderFilterset

    def get_queryset(self):
        # Using queryset defined in api/managers/order.py
        return self.queryset.for_user(self.request.user)


class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OrderSerializer(),
        },
    )
    def post(self, request):
        """
        Cancels an Order.
        Returns:
          The canceled Order.
        """
        order = Order.objects.get(id=request.data["order_id"])

        try:
            order.status = Order.Status.CANCELLED
            order.save()
            return Response(OrderSerializer(order).data)
        except Exception as e:
            raise APIException(str(e))


class OrderRescheduleView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OrderSerializer(),
        },
    )
    def post(self, request):
        """
        Reschedules an Order.
        Returns:
          The canceled Order.
        """
        order = Order.objects.get(id=request.data["order_id"])

        try:
            # order.status = Order.Status.CANCELLED
            # order.save()
            return Response(OrderSerializer(order).data)
        except Exception as e:
            raise APIException(str(e))
