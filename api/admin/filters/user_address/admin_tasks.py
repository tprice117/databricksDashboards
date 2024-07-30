from django.contrib.admin import SimpleListFilter


class UserAdddressAdminTasksFilter(SimpleListFilter):
    title = "Admin Tasks"
    parameter_name = "tasks"

    def lookups(self, request, model_admin):
        return [
            ("missing_type", "Missing Type"),
            ("missing_stripe_customer_id", "Missing Stripe Customer ID"),
            ("missing_name", "Missing Name"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "missing_type":
            return queryset.filter(user_address_type__isnull=True)
        elif self.value() == "missing_stripe_customer_id":
            return queryset.filter(stripe_customer_id__isnull=True)
        elif self.value() == "missing_name":
            return queryset.filter(name__isnull=True)
