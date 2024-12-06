import csv

from django.contrib import admin
from django.db.models import F
from django.shortcuts import redirect, render
from django.urls import path

from api.admin.filters import CreatedDateFilter
from api.admin.filters.user.user_type import UserTypeFilter
from api.admin.inlines import UserGroupUserInline
from api.forms import CsvImportForm
from api.models import Order, User, UserGroup


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    model = User
    search_fields = ["id", "email", "first_name", "last_name"]
    list_display = (
        "email",
        "first_name",
        "last_name",
        "cart_orders",
        "active_orders",
        "last_active",
    )
    ordering = [F("last_active").desc(nulls_last=True)]
    autocomplete_fields = ["user_group"]
    list_filter = (
        CreatedDateFilter,
        UserTypeFilter,
        "user_group",
    )
    inlines = [
        UserGroupUserInline,
    ]

    def cart_orders(self, obj):
        return Order.objects.filter(order_group__user=obj, submitted_on=None).count()

    def active_orders(self, obj):
        return (
            Order.objects.filter(order_group__user=obj)
            .exclude(submitted_on=None)
            .count()
        )

    change_list_template = "admin/entities/user_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("import-csv/", self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode("utf-8").splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            keys = ["user_group", "phone", "email", "first_name", "last_name"]
            for row in reader:
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(
                        request,
                        "Your csv file must have a header rows with 'user_group', 'phone', 'email', 'first_name', and 'last_name' as the first columns.",
                    )
                    return redirect("..")

            # Create User Groups.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                print(row)
                if User.objects.filter(email=row["email"]).count() == 0:
                    test, test2 = User.objects.get_or_create(
                        user_group=UserGroup.objects.get(id=row["user_group"]),
                        user_id="",
                        phone=row["phone"],
                        email=row["email"],
                        first_name=row["first_name"],
                        last_name=row["last_name"],
                        is_admin=True,
                    )
                    print(test)
                    print(test2)
                else:
                    print("USER ALREADY EXISITS: " + row["email"])

            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)
