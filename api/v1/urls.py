from django.urls import path
from rest_framework.routers import DefaultRouter

from api.v1.views import (
    OrderGroupViewSet,
    OrderViewSet,
    OrderCancelView,
    OrderRescheduleView,
    OrderGroupDeliveryView,
    OrderGroupOneTimeView,
    OrderGroupPickupView,
    OrderGroupRemovalView,
    OrderGroupSwapView,
    OrderGroupUpdateAccessDetailsView,
    OrderGroupUpdatePlacementDetailsView,
)

router = DefaultRouter()
router.register(r"orders", OrderViewSet)
router.register(r"order-groups", OrderGroupViewSet)

urlpatterns = router.urls

urlpatterns += [
    path(
        "order-groups/<uuid:order_group_id>/order/delivery/",
        OrderGroupDeliveryView.as_view(),
        name="api_booking_delivery",
    ),
    path(
        "order-groups/<uuid:order_group_id>/order/one-time/",
        OrderGroupOneTimeView.as_view(),
        name="api_booking_one_time",
    ),
    path(
        "order-groups/<uuid:order_group_id>/order/pickup/",
        OrderGroupPickupView.as_view(),
        name="api_booking_pickup",
    ),
    path(
        "order-groups/<uuid:order_group_id>/order/swap/",
        OrderGroupSwapView.as_view(),
        name="api_booking_swap",
    ),
    path(
        "order-groups/<uuid:order_group_id>/order/removal/",
        OrderGroupRemovalView.as_view(),
        name="api_booking_removal",
    ),
    path(
        "order-groups/<uuid:order_group_id>/update-access-details/",
        OrderGroupUpdateAccessDetailsView.as_view(),
        name="api_booking_update_access_details",
    ),
    path(
        "order-groups/<uuid:order_group_id>/update-placement-details/",
        OrderGroupUpdatePlacementDetailsView.as_view(),
        name="api_booking_update_placement_details",
    ),
    path(
        "orders/<uuid:order_id>/cancel/",
        OrderCancelView.as_view(),
        name="api_order_cancel",
    ),
    path(
        "orders/<uuid:order_id>/reschedule/",
        OrderRescheduleView.as_view(),
        name="api_order_reschedule",
    ),
]
