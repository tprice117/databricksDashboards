from django.contrib import admin

from api.models import UserGroupCreditApplication


class UserGroupCreditApplicationInline(admin.TabularInline):
    model = UserGroupCreditApplication
    fields = ("requested_credit_limit", "credit_report", "created_on")
    readonly_fields = ("requested_credit_limit", "created_on")
    show_change_link = True
    extra = 0
