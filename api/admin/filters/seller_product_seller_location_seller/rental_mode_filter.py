from django.contrib import admin


class RentalModeFilter(admin.SimpleListFilter):
    title = "rental mode"
    parameter_name = "rental_mode"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each tuple is the coded value
        for the option that will appear in the URL query. The second element is the
        human-readable name for the option that will appear in the right sidebar.
        """
        return (
            ("rental_one_step", "Rental One Step"),
            ("rental_one_step_missing", "Rental One Step Missing"),
            ("rental", "Rental OG"),
            ("rental_missing", "Rental OG Missing"),
            ("rental_multi_step", "Rental Multi Step"),
            ("rental_multi_step_missing", "Rental Multi Step Missing"),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value provided in the query string
        and retrievable via `self.value()`.
        """
        if self.value() == "rental_one_step":
            return queryset.filter(
                seller_product__product__main_product__has_rental_one_step=True
            )
        if self.value() == "rental_one_step_missing":
            return queryset.filter(
                seller_product__product__main_product__has_rental_one_step=True
            ).filter(rental_one_step__isnull=True)
        if self.value() == "rental":
            return queryset.filter(
                seller_product__product__main_product__has_rental=True
            )
        if self.value() == "rental_missing":
            return queryset.filter(
                seller_product__product__main_product__has_rental=True
            ).filter(rental__isnull=True)
        if self.value() == "rental_multi_step":
            return queryset.filter(
                seller_product__product__main_product__has_rental_multi_step=True
            )
        if self.value() == "rental_multi_step_missing":
            return queryset.filter(
                seller_product__product__main_product__has_rental_multi_step=True
            ).filter(rental_multi_step__isnull=True)
