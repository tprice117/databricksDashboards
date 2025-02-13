from django.contrib import admin

from admin_approvals.models import UserGroupAdminApprovalUserInvite


class UserGroupAdminApprovalUserInviteInline(admin.TabularInline):
    model = UserGroupAdminApprovalUserInvite
    fields = ("user_group", "user", "email", "status")
    raw_id_fields = ("user_group", "user")
    show_change_link = False
    extra = 0
