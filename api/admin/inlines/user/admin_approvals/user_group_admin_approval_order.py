from django.contrib import admin

from api.models import UserGroupAdminApprovalOrder


class UserGroupAdminApprovalOrderInline(admin.TabularInline):
    model = UserGroupAdminApprovalOrder
    fields = ("order", "status")
    show_change_link = False
    extra = 0
