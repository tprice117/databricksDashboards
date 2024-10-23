from django.contrib import admin

from api.models import OrderGroupAttachment


class OrderGroupAttachmentInline(admin.TabularInline):
    model = OrderGroupAttachment
    fields = ("order_group", "file")
    show_change_link = False
    extra = 0
