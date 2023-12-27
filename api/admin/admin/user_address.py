from django.contrib import admin

from api.models import UserAddress


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    model = UserAddress
    list_display = ("name", "user_group", "project_id")
    autocomplete_fields = ["user_group", "user"]
    search_fields = ["name", "street"]
