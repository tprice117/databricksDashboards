from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import (
    APIException,
    ValidationError as DRFValidationError,
)
from django_filters import rest_framework as filters

from api.filters import OrderGroupFilterset
from api.serializers import OrderGroupSerializer, OrderSerializer
from api.models import OrderGroup
from api.v1.serializers import (
    OrderGroupNewTransactionRequestSerializer,
    OrderGroupAccessDetailsRequestSerializer,
    OrderGroupPlacementDetailsRequestSerializer,
    OrderGroupListSerializer,
)
from common.utils.pagination import CustomLimitOffsetPagination


class OrderGroupViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = OrderGroup.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = OrderGroupFilterset
    pagination_class = CustomLimitOffsetPagination

    def get_queryset(self):
        # Using queryset defined in api/managers/order_group.py
        return self.queryset.for_user(self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderGroupListSerializer
        return OrderGroupSerializer


class OrderGroupDeliveryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OrderGroupNewTransactionRequestSerializer,
        responses={
            201: OrderSerializer(),
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Creates a new delivery(Order) for the OrderGroup.
        Returns:
          The Order.
        """
        order_group_id = self.kwargs.get("order_group_id")
        # Convert request into serializer.
        serializer = OrderGroupNewTransactionRequestSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise DRFValidationError(serializer.errors)

        order_group = OrderGroup.objects.get(id=order_group_id)
        delivery_date = serializer.validated_data["date"]
        schedule_window = serializer.validated_data["schedule_window"]
        try:
            order = order_group.create_delivery(
                delivery_date, schedule_window=schedule_window
            )
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            raise APIException(str(e))


class OrderGroupOneTimeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OrderGroupNewTransactionRequestSerializer,
        responses={
            201: OrderSerializer(),
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Creates a new one time(Order) for the OrderGroup.
        Returns:
          The Order.
        """
        order_group_id = self.kwargs.get("order_group_id")
        # Convert request into serializer.
        serializer = OrderGroupNewTransactionRequestSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise DRFValidationError(serializer.errors)

        order_group = OrderGroup.objects.get(id=order_group_id)
        delivery_date = serializer.validated_data["date"]
        schedule_window = serializer.validated_data["schedule_window"]
        try:
            order = order_group.create_onetime(
                delivery_date, schedule_window=schedule_window
            )
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            raise APIException(str(e))


class OrderGroupPickupView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OrderGroupNewTransactionRequestSerializer,
        responses={
            201: OrderSerializer(),
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Creates a new pickup(Order) for the OrderGroup.
        Returns:
          The Order.
        """
        order_group_id = self.kwargs.get("order_group_id")
        # Convert request into serializer.
        serializer = OrderGroupNewTransactionRequestSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise DRFValidationError(serializer.errors)

        order_group = OrderGroup.objects.get(id=order_group_id)
        pickup_date = serializer.validated_data["date"]
        schedule_window = serializer.validated_data["schedule_window"]
        try:
            order = order_group.create_pickup(
                pickup_date, schedule_window=schedule_window
            )
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            raise APIException(str(e))


class OrderGroupSwapView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OrderGroupNewTransactionRequestSerializer,
        responses={
            201: OrderSerializer(),
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Creates a new swap(Order) for the OrderGroup.
        Returns:
          The Order.
        """
        order_group_id = self.kwargs.get("order_group_id")
        # Convert request into serializer.
        serializer = OrderGroupNewTransactionRequestSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise DRFValidationError(serializer.errors)

        order_group = OrderGroup.objects.get(id=order_group_id)
        swap_date = serializer.validated_data["date"]
        schedule_window = serializer.validated_data["schedule_window"]
        try:
            order = order_group.create_swap(swap_date, schedule_window=schedule_window)
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            raise APIException(str(e))


class OrderGroupRemovalView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OrderGroupNewTransactionRequestSerializer,
        responses={
            201: OrderSerializer(),
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Creates a new removal(Order) for the OrderGroup.
        Returns:
          The Order.
        """
        order_group_id = self.kwargs.get("order_group_id")
        # Convert request into serializer.
        serializer = OrderGroupNewTransactionRequestSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise DRFValidationError(serializer.errors)

        order_group = OrderGroup.objects.get(id=order_group_id)
        removal_date = serializer.validated_data["date"]
        schedule_window = serializer.validated_data["schedule_window"]
        try:
            order = order_group.create_removal(
                removal_date, schedule_window=schedule_window
            )
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            raise APIException(str(e))


class OrderGroupUpdateAccessDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OrderGroupAccessDetailsRequestSerializer,
        responses={
            200: OrderGroupSerializer(),
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Updates the access details of the OrderGroup.
        Returns:
          The OrderGroup.
        """
        order_group_id = self.kwargs.get("order_group_id")
        # Convert request into serializer.
        serializer = OrderGroupAccessDetailsRequestSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise DRFValidationError(serializer.errors)

        order_group = OrderGroup.objects.get(id=order_group_id)
        try:
            order_group.access_details = serializer.validated_data["access_details"]
            order_group.save()
            return Response(OrderGroupSerializer(order_group).data)
        except Exception as e:
            raise APIException(str(e))


class OrderGroupUpdatePlacementDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OrderGroupPlacementDetailsRequestSerializer,
        responses={
            200: OrderGroupSerializer(),
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Updates the placement details of the OrderGroup.
        Returns:
          The OrderGroup.
        """
        order_group_id = self.kwargs.get("order_group_id")
        # Convert request into serializer.
        serializer = OrderGroupPlacementDetailsRequestSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise DRFValidationError(serializer.errors)

        order_group = OrderGroup.objects.get(id=order_group_id)
        try:
            order_group.placement_details = serializer.validated_data[
                "placement_details"
            ]
            order_group.delivered_to_street = serializer.validated_data[
                "delivered_to_street"
            ]
            order_group.save()
            return Response(OrderGroupSerializer(order_group).data)
        except Exception as e:
            raise APIException(str(e))
