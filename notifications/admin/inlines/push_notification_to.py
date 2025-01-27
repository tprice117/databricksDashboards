from django.contrib import admin

import notifications.models as models


class PushNotificationToInline(admin.StackedInline):
    model = models.PushNotificationTo
    show_change_link = True
    extra = 0
    raw_id_fields = ["user", "created_by", "updated_by"]
