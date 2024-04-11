from django.contrib import admin

from admin_approvals.models import UserGroupAdminApprovalOrder


class UserGroupAdminApprovalOrderInline(admin.TabularInline):
    model = UserGroupAdminApprovalOrder
    fields = ("order", "status")
    show_change_link = False
    extra = 0
