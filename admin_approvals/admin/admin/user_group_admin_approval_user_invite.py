from django.contrib import admin
from admin_approvals.models import UserGroupAdminApprovalUserInvite


@admin.register(UserGroupAdminApprovalUserInvite)
class UserGroupAdminApprovalUserInviteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email",
        "user_group_id",
        "user_id",
        "status",
        "created_by",
        "updated_on",
        "created_on",
    )
    list_filter = ("status", "updated_on", "created_on")
    search_fields = ("id", "email", "user__email", "user_group__name")
