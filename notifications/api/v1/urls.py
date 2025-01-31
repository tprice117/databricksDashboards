from django.urls import path

from rest_framework.routers import DefaultRouter
from notifications.api.v1.views import (
    PushNotificationViewSet,
    PushNotificationReadView,
    PushNotificationReadAllView,
)

router = DefaultRouter()
router.register(r"push-notifications", PushNotificationViewSet)

urlpatterns = router.urls

urlpatterns += [
    path(
        "push-notifications/<uuid:push_notification_id>/read/",
        PushNotificationReadView.as_view(),
        name="api_push_notification_read",
    ),
    path(
        "push-notifications/all/read/",
        PushNotificationReadAllView.as_view(),
        name="api_all_push_notifications_read",
    ),
]
