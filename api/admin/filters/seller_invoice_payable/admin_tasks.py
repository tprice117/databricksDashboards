from django.contrib.admin import SimpleListFilter


class SellerInvoicePayableAdminTasksFilter(SimpleListFilter):
    title = "Admin Tasks"
    parameter_name = "tasks"

    def lookups(self, request, model_admin):
        return [
            ("missing_invoice_file", "Missing Invoice File"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "missing_invoice_file":
            return queryset.filter(invoice_file__isnull=True)
