from typing import List, Optional

from django.db import models

from common.models.base_model import BaseModel
from pricing_engine.models.pricing_line_item import PricingLineItem


class PricingRentalMultiStepShift(BaseModel):
    two_shift = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="The multiplier for the two shift rental period. For example, "
        "if the two shift rental period is 1.5 times the hourly rate, this field "
        "should be 1.5.",
    )
    three_shift = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="The multiplier for the three shift rental period. For example, "
        "if the three shift rental period is 2 times the hourly rate, this field "
        "should be 2.",
    )

    class Meta:
        abstract = True

    def apply_shift_surcharge(
        self,
        shift_count: Optional[int],
        pricing_line_items: List[PricingLineItem],
    ) -> List[PricingLineItem]:
        """
        Depending on the 'shift_count', apply the configured surcharge to the
        `pricing_line_items`.
        """

        # Validate shift_count input (must be 1, 2, or 3).
        if shift_count not in [1, 2, 3]:
            raise Exception("The value of 'shift_count' must be 1, 2, or 3.")

        # If the shift count is 2 or 3, apply the surcharge to each PricingLineItem.
        if shift_count in [2, 3]:
            multiplier = self.two_shift if shift_count == 2 else self.three_shift

            for pricing_line_item in pricing_line_items:
                # Increase the unit_price by the multipler.
                pricing_line_item.unit_price *= multiplier

        # If shift count is 1, then leave the PricingLineItems unchanged.
        return pricing_line_items
