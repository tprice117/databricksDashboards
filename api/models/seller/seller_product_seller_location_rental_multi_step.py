from datetime import timedelta

from django.db import models

from common.models import BaseModel
from pricing_engine.models import PricingLineItem


class SellerProductSellerLocationRentalMultiStep(BaseModel):
    seller_product_seller_location = models.OneToOneField(
        "api.SellerProductSellerLocation",
        on_delete=models.CASCADE,
        related_name="rental_multi_step",
    )
    hour = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    day = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    week = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    two_weeks = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )
    month = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        null=True,
    )

    def _is_complete(self):
        return (
            self.hour is not None
            or self.day is not None
            or self.week is not None
            or self.two_weeks is not None
            or self.month is not None
        )

    # This is a workaround to make the is_complete property to display in the admin
    # as the default Django boolean icons.
    _is_complete.boolean = True
    is_complete = property(_is_complete)

    # This is a workaround to make the is_complete property to display in the admin
    # as the default Django boolean icons.
    _is_complete.boolean = True
    is_complete = property(_is_complete)

    @property
    def effective_day_rate(self):
        """
        Returns the daily rate based on hour or day field, whichever is cheaper.
        """
        if self.day and self.hour:
            return min(self.day, self.hour * 24)
        elif self.day:
            return self.day
        elif self.hour:
            return self.hour * 24
        else:
            raise ValueError("Either hour or day rate must be defined")

    @property
    def effective_week_rate(self):
        """
        Returns the weekly rate based on day or week field, whichever is cheaper.
        """
        if self.week and self.day:
            return min(self.week, self.effective_day_rate * 7)
        elif self.week:
            return self.week
        elif self.day:
            return self.effective_day_rate * 7
        else:
            raise ValueError("Either day or week rate must be defined")

    @property
    def effective_two_week_rate(self):
        """
        Returns the two-week rate based on day or two_weeks field, whichever is cheaper.
        """
        if self.two_weeks and self.day:
            return min(self.two_weeks, self.effective_day_rate * 14)
        elif self.two_weeks:
            return self.two_weeks
        elif self.day:
            return self.effective_day_rate * 14
        else:
            raise ValueError("Either day or two_weeks rate must be defined")

    @property
    def effective_month_rate(self):
        """
        Returns the monthly rate based on day or month field, whichever is cheaper.
        """
        if self.month and self.day:
            return min(self.month, self.effective_day_rate * 30)
        elif self.month:
            return self.month
        elif self.day:
            return self.effective_day_rate * 30
        else:
            raise ValueError("Either day or month rate must be defined")

    def get_price_base_hours(self, hours: int):
        return hours * float(self.hour) if self.hour else None

    def get_price_base_days(self, hours: int):
        price, remaining_hours = self._get_price_base(
            hours=hours,
            hours_per_interval=24,
            effective_interval_rate=self.effective_day_rate,
        )

        if remaining_hours > 0:
            price += remaining_hours * float(self.hour)

        return price

    def get_price_base_weeks(self, hours: int):
        price, remaining_hours = self._get_price_base(
            hours=hours,
            hours_per_interval=168,
            effective_interval_rate=self.effective_week_rate,
        )
        if remaining_hours > 0:
            price += self.get_price_base_days(remaining_hours)

        return price

    def get_price_base_two_weeks(self, hours: int):
        price, remaining_hours = self._get_price_base(
            hours=hours,
            hours_per_interval=336,
            effective_interval_rate=self.effective_two_week_rate,
        )
        if remaining_hours > 0:
            price += self.get_price_base_weeks(remaining_hours)

        return price

    def get_price_base_months(self, hours: int):
        price, remaining_hours = self._get_price_base(
            hours=hours,
            hours_per_interval=720,
            effective_interval_rate=self.effective_month_rate,
        )
        if remaining_hours > 0:
            price += self.get_price_base_days(remaining_hours)

        return price

    def _get_price_base(
        self,
        hours: int,
        hours_per_interval: int,
        effective_interval_rate: float,
    ):
        intervals = max(1, hours // hours_per_interval)

        # Get the remaining hours.
        remaining_hours = hours - (intervals * hours_per_interval)

        price = intervals * float(effective_interval_rate)

        return price, remaining_hours

    def get_price(self, duration: timedelta) -> PricingLineItem:
        """
        Calculates the most cost-efficient rental price based on duration (hours or days).

        Args:
            duration: The number of hours or days for the rental.

        Returns:
            A tuple containing the rental price (decimal) and the chosen pricing tier
            (e.g., "Hourly", "Daily", "Weekly", "Monthly").
        """
        if duration < timedelta(0):
            raise Exception("The Duration must be positive.")

        # Get the total number of hours.
        hours = duration.total_seconds() / 3600

        # Calculate the price for each pricing tier.
        hourly_price = self.get_price_base_hours(hours)
        daily_price = self.get_price_base_days(hours)
        weekly_price = self.get_price_base_weeks(hours)
        two_weeks_price = self.get_price_base_two_weeks(hours)
        monthly_price = self.get_price_base_months(hours)

        # Find the most cost-efficient pricing tier, return PriceLineItem.
        min_price = min(
            price
            for price in [
                hourly_price,
                daily_price,
                weekly_price,
                two_weeks_price,
                monthly_price,
            ]
            if price is not None
        )

        if min_price == hourly_price:
            return PricingLineItem(
                description="Hourly",
                quantity=hours,
                unit_price=self.hour,
                units="hours",
            )

        elif min_price == daily_price:
            return PricingLineItem(
                description="Daily",
                quantity=hours / 24,
                unit_price=self.effective_day_rate,
                units="days",
            )

        elif min_price == weekly_price:
            return PricingLineItem(
                description="Weekly",
                quantity=hours / 168,
                unit_price=self.effective_week_rate,
                units="weeks",
            )

        elif min_price == two_weeks_price:
            return PricingLineItem(
                description="Two Weeks",
                quantity=hours / 336,
                unit_price=self.effective_two_week_rate,
                units="weeks",
            )
        else:
            return PricingLineItem(
                description="Monthly",
                quantity=hours / 720,
                unit_price=self.effective_month_rate,
                units="months",
            )
