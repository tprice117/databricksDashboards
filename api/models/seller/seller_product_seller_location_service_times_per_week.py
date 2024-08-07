from datetime import timedelta

from django.db import models

from common.models import BaseModel
from pricing_engine.models.pricing_line_item import PricingLineItem


class SellerProductSellerLocationServiceTimesPerWeek(BaseModel):
    """
    This model represents the service times per week for a seller product seller location.
    Currently, it is specifically designed for Portable Toilet service pricing. Each price
    field represents the price for a specific number of times per week, quoted as a monthly rate.

    For example, if the one_time_per_week field is set to 100, then a customer will be charged
    100 for a portable toilet service that is serviced once per week for up to a month.
    """

    seller_product_seller_location = models.OneToOneField(
        "api.SellerProductSellerLocation",
        on_delete=models.CASCADE,
        related_name="service_times_per_week",
    )
    one_time_per_week = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    two_times_per_week = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    three_times_per_week = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    four_times_per_week = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    five_times_per_week = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.seller_product_seller_location.seller_location.name

    def _is_complete(self):
        return (
            self.one_time_per_week
            or self.two_times_per_week
            or self.three_times_per_week
            or self.four_times_per_week
            or self.five_times_per_week
        )

    # This is a workaround to make the is_complete property to display in the admin
    # as the default Django boolean icons.
    _is_complete.boolean = True
    is_complete = property(_is_complete)

    def get_price(
        self,
        times_per_week: int,
    ) -> PricingLineItem:
        if times_per_week < 0:
            raise Exception("The times_per_week must be positive.")

        if times_per_week == 1:
            return PricingLineItem(
                description="One Time Per Week",
                unit_price=self.one_time_per_week,
            )
        elif times_per_week == 2:
            return PricingLineItem(
                description="Two Times Per Week",
                unit_price=self.two_times_per_week,
            )
        elif times_per_week == 3:
            return PricingLineItem(
                description="Three Times Per Week",
                unit_price=self.three_times_per_week,
            )
        elif times_per_week == 4:
            return PricingLineItem(
                description="Four Times Per Week",
                unit_price=self.four_times_per_week,
            )
        elif times_per_week == 5:
            return PricingLineItem(
                description="Five Times Per Week",
                unit_price=self.five_times_per_week,
            )
        else:
            raise Exception("The times_per_week must be between 1 and 5.")
