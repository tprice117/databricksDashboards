from django.contrib.admin import SimpleListFilter


class DisposalLocationAdminTasksFilter(SimpleListFilter):
    title = "Admin Tasks"
    parameter_name = "tasks"

    def lookups(self, request, model_admin):
        return [
            ("missing_ticket_image", "Missing Ticket Image"),
            ("missing_disposal_location", "Missing Disposal Location"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "missing_ticket_image":
            return queryset.filter(image__isnull=True)
        elif self.value() == "missing_disposal_location":
            return queryset.filter(disposal_location__isnull=True)
