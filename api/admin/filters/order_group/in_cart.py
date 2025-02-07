from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class CartStatusFilter(admin.SimpleListFilter):
    """Simple list filter to filter OrderGroups based on whether they are in the cart or not."""

    title = "Cart Status"
    parameter_name = "in_cart"

    def lookups(self, request, model_admin):
        return [
            ("true", _("In Cart")),
            ("false", _("Not In Cart")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "true":
            return queryset.filter(
                orders__isnull=False,
                orders__submitted_on__isnull=True,
            )
        elif self.value() == "false":
            return (
                queryset.filter(
                    orders__isnull=False,
                )
                .exclude(
                    orders__submitted_on__isnull=True,
                )
                .distinct()
            )
        else:
            return queryset
