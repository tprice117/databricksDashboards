from datetime import timedelta, timezone

from django.contrib.admin import SimpleListFilter


class SellerLocationAdminTasksFilter(SimpleListFilter):
    title = "Admin Tasks"
    parameter_name = "tasks"

    def lookups(self, request, model_admin):
        return [
            ("missing_payee_name", "Missing Payee Name"),
            ("missing_order_email", "Missing Order Email"),
            ("missing_order_phone", "Missing Order Phone"),
            ("missing_gi_coi", "Missing GI COI"),
            ("missing_gi_coi_expiration_date", "Missing GI COI Expiration Date"),
            ("missing_gi_gl_limit", "Missing GI GL Limit"),
            ("missing_auto_coi", "Missing Auto COI"),
            ("missing_auto_coi_expiration_date", "Missing Auto COI Expiration Date"),
            ("missing_auto_limit", "Missing Auto Limit"),
            ("missing_workers_comp_coi", "Missing Workers Comp COI"),
            (
                "missing_workers_comp_coi_expiration_date",
                "Missing Workers Comp COI Expiration Date",
            ),
            ("missing_workers_comp_limit", "Missing Workers Comp Limit"),
            ("missing_w9", "Missing W9"),
            ("gi_coi_expiration_date_60days", "GI COI Expires within 60 Days"),
            ("auto_coi_expiration_date_60days", "Auto COI Expires within 60 Days"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "missing_payee_name":
            return queryset.filter(payee_name__isnull=True)
        elif self.value() == "missing_order_email":
            return queryset.filter(order_email__isnull=True)
        elif self.value() == "missing_order_phone":
            return queryset.filter(order_phone__isnull=True)
        elif self.value() == "missing_gl_coi":
            return queryset.filter(gl_coi__isnull=True)
        elif self.value() == "missing_gl_coi_expiration_date":
            return queryset.filter(gl_coi_expiration_date__isnull=True)
        elif self.value() == "missing_gl_limit":
            return queryset.filter(gl_limit__isnull=True)
        elif self.value() == "missing_auto_coi":
            return queryset.filter(auto_coi__isnull=True)
        elif self.value() == "missing_auto_coi_expiration_date":
            return queryset.filter(auto_coi_expiration_date__isnull=True)
        elif self.value() == "missing_auto_limit":
            return queryset.filter(auto_limit__isnull=True)
        elif self.value() == "missing_workers_comp_coi":
            return queryset.filter(workers_comp_coi__isnull=True)
        elif self.value() == "missing_workers_comp_coi_expiration_date":
            return queryset.filter(workers_comp_coi_expiration_date__isnull=True)
        elif self.value() == "missing_workers_comp_limit":
            return queryset.filter(workers_comp_limit__isnull=True)
        elif self.value() == "missing_w9":
            return queryset.filter(w9__isnull=True)
        elif self.value() == "gi_coi_expiration_date_60days":
            return queryset.filter(
                gl_coi_expiration_date__lte=timezone.now() + timedelta(days=60)
            )
        elif self.value() == "auto_coi_expiration_date_60days":
            return queryset.filter(
                auto_coi_expiration_date__lte=timezone.now() + timedelta(days=60)
            )
