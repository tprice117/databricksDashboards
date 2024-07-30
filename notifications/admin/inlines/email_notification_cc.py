from django.contrib import admin

import notifications.models as models


class EmailNotificationCcInline(admin.StackedInline):
    model = models.EmailNotificationCc
    show_change_link = True
    extra = 0
