from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class StatusFilter(admin.SimpleListFilter):
    title = _("Status")
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return (
            ("active", _("Active")),
            ("needs_attention", _("Needs Attention")),
            ("inactive", _("Inactive")),
        )

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.get_active()
        if self.value() == "needs_attention":
            return queryset.get_needs_attention()
        if self.value() == "inactive":
            return queryset.get_inactive()
        return queryset
