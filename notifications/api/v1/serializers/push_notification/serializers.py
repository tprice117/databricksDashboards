from rest_framework import serializers

from notifications.models import PushNotification


class PushNotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = PushNotification
        fields = "__all__"


class PushNotificationReadAllResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.CharField()
    read_count = serializers.IntegerField()
