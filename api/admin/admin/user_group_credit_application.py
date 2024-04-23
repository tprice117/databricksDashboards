from django.contrib import admin

from api.models import UserGroupCreditApplication


@admin.register(UserGroupCreditApplication)
class UserGroupCreditApplicationAdmin(admin.ModelAdmin):
    model = UserGroupCreditApplication
