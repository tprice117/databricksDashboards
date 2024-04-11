from django.contrib import admin

from api.models import User


class UserInline(admin.TabularInline):
    model = User
    fields = (
        "is_admin",
        "first_name",
        "last_name",
        "email",
        "phone",
    )
    readonly_fields = ("first_name", "last_name", "email", "phone")
    show_change_link = True
    extra = 0
