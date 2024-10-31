from django.contrib.admin import SimpleListFilter


class UserTypeFilter(SimpleListFilter):
    title = "User Type"
    parameter_name = "type"

    def lookups(self, request, model_admin):
        return [
            ("customer_business", "Customer (Business)"),
            ("customer_consumer", "Customer (Consumer)"),
            ("supplier", "Supplier"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "customer_business":
            return queryset.filter(
                is_staff=False,
                user_group__isnull=False,
                user_group__seller__isnull=True,
            )
        elif self.value() == "customer_consumer":
            return queryset.filter(
                is_staff=False,
                user_group__isnull=True,
            )
        elif self.value() == "supplier":
            return queryset.filter(
                is_staff=False,
                user_group__seller__isnull=False,
            )
