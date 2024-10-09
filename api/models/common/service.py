from django.db import models

from common.models import BaseModel
from pricing_engine.models import PricingLineItem
from decimal import Decimal
from math import ceil


class PricingService(BaseModel):
    """
    This model represents the service pricing for a seller product seller location. Currently,
    it is specifically designed for services that are priced per mile or as a flat rate. The
    price_per_mile field represents the price per mile for the service. The flat_rate_price
    field represents the flat rate price for the service.
    """

    price_per_mile = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    flat_rate_price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )

    class Meta:
        abstract = True

    def _is_complete(self):
        return (self.price_per_mile is not None and self.price_per_mile > 0) or (
            self.flat_rate_price is not None and self.flat_rate_price > 0
        )

    # This is a workaround to make the is_complete property to display in the admin
    # as the default Django boolean icons.
    _is_complete.boolean = True
    is_complete = property(_is_complete)

    def get_price(
        self,
        miles: Decimal,
    ) -> list[PricingLineItem]:
        items: list[PricingLineItem]
        items = []

        # Handle the case where the service is priced per mile.
        if self.price_per_mile is not None:
            items.append(
                PricingLineItem(
                    description="Service",
                    units="Miles",
                    quantity=ceil(miles),
                    unit_price=self.price_per_mile,
                )
            )

        # Handle the case where the service is a flat rate.
        if self.flat_rate_price is not None:

            items.append(
                PricingLineItem(
                    description="Flat Rate",
                    unit_price=self.flat_rate_price,
                )
            )

        return items
