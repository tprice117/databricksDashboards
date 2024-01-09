from django.contrib import admin

import notifications.admin.inlines as inlines
import notifications.models as models


@admin.register(models.EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    list_display = [
        "from_email",
        "subject",
        "sent_at",
    ]
    inlines = [
        inlines.EmailNotificationToInline,
        inlines.EmailNotificationBccInline,
        inlines.EmailNotificationCcInline,
        inlines.EmailNotificationAttachmentInline,
    ]
