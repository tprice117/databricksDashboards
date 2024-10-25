from django.contrib.admin import SimpleListFilter


class UserTypeFilter(SimpleListFilter):
    title = "User Type"
    parameter_name = "type"

    def lookups(self, request, model_admin):
        return [
            ("customer", "Customer"),
            ("supplier", "Supplier"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "customer":
            return queryset.filter(seller__isnull=True)
        elif self.value() == "supplier":
            return queryset.filter(seller__isnull=False)
