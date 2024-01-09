from django.contrib import admin

import notifications.models as models


class EmailNotificationAttachmentInline(admin.StackedInline):
    model = models.EmailNotificationAttachment
    show_change_link = True
    extra = 0
