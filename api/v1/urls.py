from django.urls import path
from rest_framework.routers import DefaultRouter

from api.v1.views import (
    OrderGroupViewSet,
    OrderViewSet,
    OrderCancelView,
    OrderRescheduleView,
    OrderGroupDeliveryView,
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
        name="cart",
    ),
    path(
        "order-groups/<uuid:order_group_id>/order/swap/",
        OrderGroupSwapView.as_view(),
        name="cart",
    ),
    path(
        "order-groups/<uuid:order_group_id>/order/removal/",
        OrderGroupRemovalView.as_view(),
        name="cart",
    ),
    path(
        "order-groups/<uuid:order_group_id>/update-access-details/",
        OrderGroupUpdateAccessDetailsView.as_view(),
        name="cart",
    ),
    path(
        "order-groups/<uuid:order_group_id>/update-placement-details/",
        OrderGroupUpdatePlacementDetailsView.as_view(),
        name="cart",
    ),
    path(
        "orders/<uuid:order_id>/cancel/",
        OrderCancelView.as_view(),
        name="order_cancel",
    ),
    path(
        "orders/<uuid:order_id>/reschedule/",
        OrderRescheduleView.as_view(),
        name="order_reschedule",
    ),
]
