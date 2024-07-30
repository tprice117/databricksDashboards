from django.contrib import admin

from admin_approvals.models import UserGroupAdminApprovalUserInvite


@admin.register(UserGroupAdminApprovalUserInvite)
class UserGroupAdminApprovalUserInviteAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "user_group",
        "user",
        "status",
        "created_by",
        "created_on",
    )
    list_filter = ("status", "updated_on", "created_on")
    search_fields = ("id", "email", "user__email", "user_group__name")
