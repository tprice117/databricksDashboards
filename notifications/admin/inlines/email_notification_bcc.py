from django.contrib import admin

import notifications.models as models


class EmailNotificationBccInline(admin.StackedInline):
    model = models.EmailNotificationBcc
    show_change_link = True
    extra = 0
