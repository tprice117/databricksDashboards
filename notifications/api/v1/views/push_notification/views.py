from django.utils import timezone

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import APIException

from notifications.api.v1.serializers import PushNotificationSerializer
from notifications.models import PushNotification, PushNotificationTo


class PushNotificationViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    queryset = PushNotification.objects.all()
    serializer_class = PushNotificationSerializer

    def get_queryset(self):
        # Using queryset defined in api/managers/order.py
        return self.queryset.for_user(self.request.user)


class PushNotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Mark all Push Notifications of logged in user as read.
        Returns:
          200 Ok.
        """

        try:
            PushNotificationTo.objects.filter(
                user=self.request.user, is_read=False
            ).update(is_read=True, read_at=timezone.now())
            return Response("OK", status=status.HTTP_200_OK)
        except Exception as e:
            raise APIException(str(e))


class PushNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: PushNotificationSerializer(),
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Mark a Push Notification as read.
        Returns:
          The Push Notification.
        """
        push_notification_id = self.kwargs.get("push_notification_id")

        push_notification = PushNotification.objects.get(id=push_notification_id)
        try:
            push_notification.read(self.request.user)
            push_notification.is_read = True
            return Response(PushNotificationSerializer(push_notification).data)
        except Exception as e:
            raise APIException(str(e))
