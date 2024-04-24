from django.contrib import admin
from admin_approvals.models import UserGroupAdminApprovalOrder


@admin.register(UserGroupAdminApprovalOrder)
class UserGroupAdminApprovalOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "status", "updated_on", "created_on"]
    list_filter = ["status", "updated_on", "created_on"]
    search_fields = ["id", "order_id", "order__order_group__user__email"]
    readonly_fields = ["id", "created_on"]
    ordering = ["-created_on"]
