from django.contrib import admin

from api.models import UserGroupPolicyInvitationApproval


class UserGroupPolicyInvitationApprovalInline(admin.TabularInline):
    model = UserGroupPolicyInvitationApproval
    fields = ("user_group", "user_type")
    show_change_link = False
    extra = 0
