from django.contrib import admin

from api.models import UserGroupAdminApprovalUserInvite


class UserGroupAdminApprovalUserInviteInline(admin.TabularInline):
    model = UserGroupAdminApprovalUserInvite
    fields = ("user_group", "user", "email", "status")
    show_change_link = False
    extra = 0
