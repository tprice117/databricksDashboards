from django.contrib import admin

from api.models import OrderAdjustment


class OrderAdjustmentInline(admin.TabularInline):
    model = OrderAdjustment
    show_change_link = True
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
