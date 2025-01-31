from rest_framework import serializers

from notifications.models import PushNotification


class PushNotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    def get_is_read(self, obj) -> bool:
        push_to = obj.push_notification_tos.filter(
            user=self.context["request"].user
        ).first()
        if push_to:
            return push_to.is_read
        return False

    class Meta:
        model = PushNotification
        fields = "__all__"
