import math
from datetime import timedelta

from django.db import models

from common.models import BaseModel
from pricing_engine.models.pricing_line_item import PricingLineItem


class PricingRentalOneStep(BaseModel):
    """
    The OneStep pricing model represents rentals that are priced
    on at a flat-rate per month. The rental rate is for up to 28 days.
    If a rental extends for greater than 28 days, a second charge of
    the rate will be added.

    ------------------------
    Example:
    Rental for 30 days.
    Days 1-28: Price is [rate].
    Days 29-30: Price is [rate].
    ----------
    Total Price: [rate] x 2.
    """

    rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )

    class Meta:
        abstract = True

    def _is_complete(self):
        return self.rate and self.rate > 0

    # This is a workaround to make the is_complete property to display in the admin
    # as the default Django boolean icons.
    _is_complete.boolean = True
    is_complete = property(_is_complete)

    def get_price(self, duration: timedelta) -> PricingLineItem:
        if duration < timedelta(0):
            raise Exception("The Duration must be positive.")

        if self.rate is None:
            # Ensure the unit_price is never None otherwise it could error
            # in order._add_fuel_and_environmental().
            raise Exception(f"The rate must be set on PricingRentalOneStep {self.id}.")

        # Get the quanity of 28 day periods for the rental.
        periods = math.ceil(duration.days / 28) if duration.days != 0 else 1

        # Create a PricingLineItem for each period.
        return PricingLineItem(
            description=None,
            units="month",
            quantity=periods,
            unit_price=self.rate,
        )
