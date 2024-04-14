from django.contrib import admin

from api.models import UserGroupUser


class UserGroupUserInline(admin.TabularInline):
    model = UserGroupUser
    fields = ("user_group", "user")
    show_change_link = True
    extra = 0
