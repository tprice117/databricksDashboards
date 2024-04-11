from django.contrib import admin

from admin_policies.models import UserGroupPolicyInvitationApproval


class UserGroupPolicyInvitationApprovalInline(admin.TabularInline):
    model = UserGroupPolicyInvitationApproval
    fields = ("user_group", "user_type")
    show_change_link = False
    extra = 0
    max_num = 2
