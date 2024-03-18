from django.core.exceptions import ValidationError
from django.db import models

from common.models import BaseModel

from .payment_method import PaymentMethod


class PaymentMethodUser(BaseModel):
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.CASCADE,
        related_name="payment_method_users",
    )
    user = models.ForeignKey(
        "api.User",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ("payment_method", "user")

    def clean(self) -> None:
        super().clean()

        # Ensure the user is part of the user group
        # associated with the payment method.
        if self.payment_method.user_group != self.user.user_group:
            raise ValidationError(
                "User is not part of the user group associated "
                "with the payment method."
            )
