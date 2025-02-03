from rest_framework import serializers

from notifications.models import PushNotification


class PushNotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = PushNotification
        fields = "__all__"
