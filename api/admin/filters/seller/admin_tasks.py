from django.contrib.admin import SimpleListFilter

from api.models import Seller


class SellerAdminTasksFilter(SimpleListFilter):
    title = "Admin Tasks"
    parameter_name = "tasks"

    def lookups(self, request, model_admin):
        return [
            ("missing_location_logo_url", "Missing Location Logo URL"),
            ("no_seller_locations", "No Seller Locations"),
            ("no_seller_products", "No Seller Products"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "missing_location_logo_url":
            return queryset.filter(location_logo_url__isnull=True)
        elif self.value() == "no_seller_locations":
            seller: Seller
            for seller in queryset:
                # Filter out sellers with at least one seller location.
                if seller.seller_locations.count() > 0:
                    queryset = queryset.exclude(id=seller.id)

            # Return the queryset with sellers that have no seller locations.
            return queryset
        elif self.value() == "no_seller_products":
            seller: Seller
            for seller in queryset:
                # Filter out sellers with at least one seller product.
                if seller.seller_products.count() > 0:
                    queryset = queryset.exclude(id=seller.id)

            # Return the queryset with sellers that have no seller products.
            return queryset
