from rest_framework import serializers

from notifications.models import PushNotification


class PushNotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    def get_is_read(self, obj) -> bool:
        return (
            obj.push_notification_tos.filter(user=self.context["request"].user)
            .first()
            .is_read
        )

    class Meta:
        model = PushNotification
        fields = "__all__"
