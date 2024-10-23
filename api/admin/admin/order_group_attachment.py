from django.contrib import admin

from api.models import OrderGroupAttachment


@admin.register(OrderGroupAttachment)
class OrderGroupAttachmentAdmin(admin.ModelAdmin):
    search_fields = [
        "order_group__id",
        "order_group__user_address__name",
        "order_group__user__email",
        "order_group__user_group__name",
    ]
    list_display = ("order_group",)
    raw_id_fields = ("order_group",)
