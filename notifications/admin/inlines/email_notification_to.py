from django.contrib import admin

import notifications.models as models


class EmailNotificationToInline(admin.StackedInline):
    model = models.EmailNotificationTo
    show_change_link = True
    extra = 0
