from itertools import chain

from django.contrib.admin import SimpleListFilter


class UserGroupAdminTasksFilter(SimpleListFilter):
    title = "Admin Tasks"
    parameter_name = "tasks"

    def lookups(self, request, model_admin):
        return [
            ("missing_credit_line_limit", "Missing Credit Line Limit"),
            ("compliance_status_needs_attention", "Compliance Status Needs Attention"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "missing_credit_line_limit":
            return queryset.filter(credit_line_limit__isnull=True)
        elif self.value() == "compliance_status_needs_attention":
            requested = queryset.filter(compliance_status="REQUESTED")
            in_progress = queryset.filter(compliance_status="IN-PROGRESS")
            needs_reviewed = queryset.filter(compliance_status="NEEDS_REVIEW")
            return list(chain(requested, in_progress, needs_reviewed))
