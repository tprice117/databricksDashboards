from django.db import models
from django.utils.translation import gettext_lazy as _

from api.models.order.order import Order
from common.models import BaseModel


class OrderReview(BaseModel):
    class Experience(models.IntegerChoices):
        """Overall experience rating for a transaction.

        Attributes:
            NEGATIVE (int): Represents a negative experience (0, "Thumbs Down").
            POSITIVE (int): Represents a positive experience (1, "Thumbs Up").
        """

        NEGATIVE = 0, _("Thumbs Down")
        POSITIVE = 1, _("Thumbs Up")

    class StarRating(models.IntegerChoices):
        """Star rating for various aspects of a transaction. Based on 5-point scale.

        Attributes:
            UNACCEPTABLE (int): Represents an unacceptable rating (1, "Unacceptable").
            UNSATISFACTORY (int): Represents an unsatisfactory rating (2, "Unsatisfactory").
            NEUTRAL (int): Represents a neutral rating (3, "Neutral").
            SATISFACTORY (int): Represents a satisfactory rating (4, "Satisfactory").
            EXCEPTIONAL (int): Represents an exceptional rating (5, "Exceptional").
        """

        UNACCEPTABLE = 1, _("Unacceptable")
        UNSATISFACTORY = 2, _("Unsatisfactory")
        NEUTRAL = 3, _("Neutral")
        SATISFACTORY = 4, _("Satisfactory")
        EXCEPTIONAL = 5, _("Exceptional")

    # Each transaction can only have one review
    order = models.OneToOneField(
        Order,
        models.CASCADE,
        related_name="review",
    )

    # Primary question (cannot be null)
    rating = models.BooleanField(
        choices=Experience.choices,
        help_text="How was your experience?",
        verbose_name="Overall Experience Rating",
    )

    # Secondary questions (optional)
    professionalism = models.IntegerField(
        choices=StarRating.choices,
        null=True,
        blank=True,
        help_text="How was the seller's professionalism?",
    )
    communication = models.IntegerField(
        choices=StarRating.choices,
        null=True,
        blank=True,
        help_text="How was the seller's communication?",
    )
    pricing = models.IntegerField(
        choices=StarRating.choices,
        null=True,
        blank=True,
        help_text="How was the seller's pricing?",
    )
    timeliness = models.IntegerField(
        choices=StarRating.choices,
        null=True,
        blank=True,
        help_text="How was the seller's timeliness?",
    )
    comment = models.TextField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Please provide any additional feedback.",
    )

    class Meta:
        verbose_name = "Transaction Review"
        verbose_name_plural = "Transaction Reviews"

    @property
    def is_positive(self):
        return self.rating == self.Experience.POSITIVE

    def __str__(self):
        return f"Review{self.id}"
