from itertools import chain

from django.contrib.admin import SimpleListFilter

from api.models import UserGroup


class UserGroupAdminTasksFilter(SimpleListFilter):
    title = "Admin Tasks"
    parameter_name = "tasks"

    def lookups(self, request, model_admin):
        return [
            ("missing_credit_line_limit", "Missing Credit Line Limit"),
            ("compliance_status_needs_attention", "Compliance Status Needs Attention"),
            ("missing_user_group_billing", "Missing User Group Billing"),
            ("missing_user_group_legal", "Missing User Group Legal"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "missing_credit_line_limit":
            return queryset.filter(credit_line_limit__isnull=True)
        elif self.value() == "compliance_status_needs_attention":
            requested = queryset.filter(compliance_status="REQUESTED")
            in_progress = queryset.filter(compliance_status="IN-PROGRESS")
            needs_reviewed = queryset.filter(compliance_status="NEEDS_REVIEW")
            return list(chain(requested, in_progress, needs_reviewed))
        elif self.value() == "missing_user_group_billing":
            user_group: UserGroup
            for user_group in queryset:
                # Filter out user groups with user group billing model.
                if hasattr(user_group, "billing"):
                    queryset = queryset.exclude(id=user_group.id)
            return queryset
        elif self.value() == "missing_user_group_legal":
            user_group: UserGroup
            for user_group in queryset:
                # Filter out user groups with user group legal model.
                if hasattr(user_group, "legal"):
                    queryset = queryset.exclude(id=user_group.id)
            return queryset
