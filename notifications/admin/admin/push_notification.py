from django.contrib import admin

import notifications.admin.inlines as inlines
import notifications.models as models


@admin.register(models.PushNotification)
class PushNotificationAdmin(admin.ModelAdmin):
    actions = ["send_push"]

    def send_push(self, request, queryset):
        for notification in queryset:
            notification.send()
        self.message_user(request, "Push Notifications sent.")

    list_display = [
        "title",
        "message",
        "created_on",
        "sent_at",
    ]
    inlines = [inlines.PushNotificationToInline]
    list_filter = ["template_id", "sent_at"]
    search_fields = ["id", "title", "push_notification_tos__user__email"]
    raw_id_fields = ["created_by", "updated_by"]
