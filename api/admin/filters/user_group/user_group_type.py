from django.contrib.admin import SimpleListFilter


class UserGroupTypeFilter(SimpleListFilter):
    title = "Type"
    parameter_name = "type"

    def lookups(self, request, model_admin):
        return [
            ("seller", "Seller"),
            ("customer", "Customer"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "seller":
            return queryset.filter(seller__isnull=False)
        elif self.value() == "customer":
            return queryset.filter(seller__isnull=True)
