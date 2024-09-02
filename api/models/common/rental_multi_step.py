from datetime import timedelta
from typing import List, Optional

from django.db import models

from common.models import BaseModel
from pricing_engine.models import PricingLineItem


class PricingRentalMultiStep(BaseModel):
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

    class Meta:
        abstract = True

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

        if remaining_hours > 0 and self.hour:
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

    def get_most_efficient_pricing_pieces(self, duration: timedelta):
        """
        Calculates the most cost-efficient combination of rental price pieces (hourly, daily, weekly, etc.)
        based on duration.

        Returns:
            A tuple containing the number of months, two-week periods, weeks, days, and hours.
        """
        if duration < timedelta(0):
            raise Exception("The Duration must be positive.")

        # Get the total number of hours.
        total_hours = duration.total_seconds() / 3600

        # Create list of PricingLineItems.
        hours = None
        days = None
        weeks = None
        two_weeks = None
        months = None

        remaining_hours = total_hours

        if remaining_hours // 720 > 0 and self.month:
            # Get whole months.
            months = remaining_hours // 720

            # Get remaining hours and price.
            remaining_hours = remaining_hours % 720

        if remaining_hours // 336 > 0 and self.two_weeks:
            # Get whole two-week periods.
            two_weeks = remaining_hours // 336

            # Get remaining hours and price.
            remaining_hours = remaining_hours % 336

        if remaining_hours // 168 > 0 and self.week:
            # Get whole weeks.
            weeks = remaining_hours // 168

            # Get remaining hours and price.
            remaining_hours = remaining_hours % 168

        if remaining_hours // 24 > 0 and self.effective_day_rate:
            # Get whole days.
            days = remaining_hours // 24

            # Get remaining hours and price.
            remaining_hours = remaining_hours % 24

        # NOTE: The following code is commented out because we are not using
        # hourly pricing currently. This is a future enhancement.

        # if remaining_hours > 0:
        #     hours = math.ceil(remaining_hours)

        return months, two_weeks, weeks, days, hours

    def get_price(
        self,
        duration: timedelta,
        shift_count: Optional[int],
    ) -> List[PricingLineItem]:
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

        months, two_weeks, weeks, days, hours = self.get_most_efficient_pricing_pieces(
            duration=duration
        )

        # Create list of PricingLineItems.
        pricing_line_items: List[PricingLineItem] = []

        if months:
            pricing_line_items.append(
                PricingLineItem(
                    description=None,
                    quantity=months,
                    unit_price=self.effective_month_rate,
                    units="months",
                )
            )

        if two_weeks:
            pricing_line_items.append(
                PricingLineItem(
                    description=None,
                    quantity=two_weeks,
                    unit_price=self.effective_two_week_rate,
                    units="two weeks",
                )
            )

        if weeks:
            pricing_line_items.append(
                PricingLineItem(
                    description=None,
                    quantity=weeks,
                    unit_price=self.effective_week_rate,
                    units="weeks",
                )
            )

        if days:
            pricing_line_items.append(
                PricingLineItem(
                    description=None,
                    quantity=days,
                    unit_price=self.effective_day_rate,
                    units="days",
                )
            )

        # NOTE: The following code is commented out because we are not using
        # hourly pricing currently. This is a future enhancement.

        # if hours:
        #     pricing_line_items.append(
        #         PricingLineItem(
        #             description=None,
        #             quantity=hours,
        #             unit_price=self.hour,
        #             units="hours",
        #         )
        #     )

        # Handle shift-based pricing, if exists.
        if hasattr(self, "rental_multi_step_shift"):
            pricing_line_items = self.rental_multi_step_shift.apply_shift_surcharge(
                shift_count=shift_count,
                pricing_line_items=pricing_line_items,
            )

        return pricing_line_items
