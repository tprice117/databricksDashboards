from django.contrib import admin
from django.http import HttpResponseRedirect
from django.utils.html import format_html

import notifications.admin.inlines as inlines
import notifications.models as models


def parse_order_id(s):
    start = s.rfind("[") + 1
    end = s.find("]", start)
    if start > 0 and end > 0:
        return s[start:end]
    else:
        return None


@admin.register(models.EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    actions = ["view_order_email"]

    def view_order_email(self, request, queryset):
        view_link = None
        for email_notification in queryset:
            find_start = "https://api"
            start = email_notification.html_content.find(f'href="{find_start}')
            if start == -1:
                find_start = "https://portal"
                start = email_notification.html_content.find(f'href="{find_start}')
            if start > 0:
                start += len('href="')
                # NOTE: This shows the the booking details page for the order.
                # Could also get order_id from view_link and get order.seller_view_order_url for old view.
                end = email_notification.html_content.find('"', start)
                view_link = email_notification.html_content[start:end]
                break
        if view_link:
            print(view_link)
            return HttpResponseRedirect(view_link)

    def order_link(self, obj):
        order_id = parse_order_id(obj.subject)
        if order_id:
            return format_html(
                f"""<a href='/admin/api/order/?q={order_id}' target="_blank">link</a>"""
            )
        else:
            return "N/A"

    list_display = ["from_email", "subject", "sent_at", "order_link"]
    inlines = [
        inlines.EmailNotificationToInline,
        inlines.EmailNotificationBccInline,
        inlines.EmailNotificationCcInline,
        inlines.EmailNotificationAttachmentInline,
    ]
    search_fields = ["from_email", "subject", "email_notification_tos__email"]
