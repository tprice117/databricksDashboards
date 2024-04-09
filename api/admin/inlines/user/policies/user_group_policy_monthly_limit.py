from django.contrib import admin

from api.models import UserGroupPolicyMonthlyLimit


class UserGroupPolicyMonthlyLimitInline(admin.TabularInline):
    model = UserGroupPolicyMonthlyLimit
    fields = ("user_group", "amount")
    show_change_link = False
    extra = 0
