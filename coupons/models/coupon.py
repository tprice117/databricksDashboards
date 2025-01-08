from django.db import models
from django.utils import timezone

from common.models import BaseModel


class Coupon(BaseModel):
    class Type(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED_AMOUNT = "fixed_amount", "Fixed Amount"

    code = models.CharField(
        max_length=50,
        unique=True,
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
    )

    # Coupon validity.
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(
        default=True,
    )

    # Discount values.
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="For percentage discounts, enter as a percentage "
        "without the percent symbol (ex: 25.00). For fixed amount "
        "discounts, enter as a dollar amount (ex: 25.00).",
    )
    max_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum discount amount allowed. For example, if "
        "the coupon is for 10% off, but the maximum discount "
        "amount is $50, the discount will be capped at $50.",
    )

    def __str__(self):
        return f"{self.code} | {self.valid_from} - {self.valid_to} | {self.text}"

    @property
    def is_valid(self):
        return self.valid_from <= timezone.now() <= self.valid_to

    @property
    def text(self):
        if self.type == self.Type.PERCENTAGE:
            return f"{self.value}% off{f', up to ${self.max_value}' if self.max_value else ''}"
        else:
            return f"${self.value} off"
