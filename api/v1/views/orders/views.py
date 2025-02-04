from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
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
from api.v1.serializers import (
    OrderRescheduleRequestSerializer,
    OrderScheduleWindowRequestSerializer,
)


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
    def post(self, request, *args, **kwargs):
        """
        Cancels an Order.
        Returns:
          The canceled Order.
        """
        order_id = self.kwargs.get("order_id")
        order = Order.objects.get(id=order_id)

        try:
            order.cancel_order()
            return Response(OrderSerializer(order).data)
        except Exception as e:
            raise APIException(str(e))


class OrderRescheduleView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OrderRescheduleRequestSerializer,
        responses={
            200: OrderSerializer(),
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Reschedules an Order.
        Returns:
          The rescheduled Order.
        """
        order_id = self.kwargs.get("order_id")
        # Convert request into serializer.
        serializer = OrderRescheduleRequestSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise DRFValidationError(serializer.errors)

        order = Order.objects.get(id=order_id)

        try:
            service_date = serializer.validated_data["date"]
            order.reschedule_order(service_date)
            return Response(OrderSerializer(order).data)
        except ValidationError as e:
            raise DRFValidationError(str(e))
        except Exception as e:
            raise APIException(str(e))


class OrderScheduleWindowView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OrderScheduleWindowRequestSerializer,
        responses={
            200: OrderSerializer(),
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Updates an Order ScheduleWindow.
        Returns:
          The Order.
        """
        order_id = self.kwargs.get("order_id")
        # Convert request into serializer.
        serializer = OrderScheduleWindowRequestSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise DRFValidationError(serializer.errors)

        order = Order.objects.get(id=order_id)

        try:
            schedule_window = serializer.validated_data["schedule_window"]
            order.update_schedule_window(schedule_window)
            return Response(OrderSerializer(order).data)
        except ValidationError as e:
            raise DRFValidationError(str(e))
        except Exception as e:
            raise APIException(str(e))
