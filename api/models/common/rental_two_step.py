from datetime import timedelta

from django.db import models

from common.models import BaseModel
from pricing_engine.models import PricingLineItem


class PricingRentalTwoStep(BaseModel):
    included_days = models.IntegerField(
        default=0,
    )
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

    class Meta:
        abstract = True

    @property
    def base_price(self):
        return self.price_per_day_included * self.included_days

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
    ) -> list[PricingLineItem]:
        if duration < timedelta(0):
            raise Exception("The Duration must be positive.")

        # Included day price (always charged).
        included_price = PricingLineItem(
            description="Included",
            units="Days",
            quantity=self.included_days,
            unit_price=self.price_per_day_included,
        )

        # Additional days price (if needed).
        additional_days = (
            duration.days - self.included_days
            if duration.days > self.included_days
            else 0
        )

        if additional_days > 0:
            additional_days_price = PricingLineItem(
                description="Additional",
                units="Days",
                quantity=additional_days,
                unit_price=self.price_per_day_additional,
            )

            return [
                included_price,
                additional_days_price,
            ]
        else:
            return [
                included_price,
            ]
