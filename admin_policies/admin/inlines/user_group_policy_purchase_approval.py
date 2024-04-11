from django.contrib import admin

from admin_policies.models import UserGroupPolicyPurchaseApproval


class UserGroupPolicyPurchaseApprovalInline(admin.TabularInline):
    model = UserGroupPolicyPurchaseApproval
    fields = ("user_group", "user_type", "amount")
    show_change_link = False
    extra = 0
