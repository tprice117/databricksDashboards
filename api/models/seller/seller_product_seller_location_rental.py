from datetime import timedelta

from django.db import models

from common.models import BaseModel


class SellerProductSellerLocationRental(BaseModel):
    seller_product_seller_location = models.OneToOneField(
        "api.SellerProductSellerLocation",
        on_delete=models.CASCADE,
        related_name="rental",
    )
    included_days = models.IntegerField(default=0)
    price_per_day_included = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    price_per_day_additional = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.seller_product_seller_location.seller_location.name

    def _is_complete(self) -> bool:
        return (
            self.price_per_day_included is not None
            and self.price_per_day_included > 0
            and self.price_per_day_additional is not None
            and self.price_per_day_additional > 0
        )

    # This is a workaround to make the is_complete property to display in the admin
    # as the default Django boolean icons.
    _is_complete.boolean = True
    is_complete = property(_is_complete)

    def get_price(
        self,
        duration: timedelta,
    ):
        if duration < timedelta(0):
            raise Exception("The Duration must be positive.")

        # Included day price (always charged).
        included_price = self.included_days * self.price_per_day_included

        # Additional days price (if needed).
        additional_days = (
            duration.days - self.included_days
            if duration.days > self.included_days
            else 0
        )
        additional_days_price = additional_days * self.price_per_day_additional

        return included_price + additional_days_price
