from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from api.models import UserAddress
from common.models import BaseModel

from .payment_method import PaymentMethod


class PaymentMethodUserAddress(BaseModel):
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.CASCADE,
        related_name="payment_method_user_addresses",
    )
    user_address = models.ForeignKey(
        UserAddress,
        on_delete=models.CASCADE,
        related_name="payment_method_user_addresses",
    )

    class Meta:
        unique_together = ("payment_method", "user_address")

    def clean(self) -> None:
        super().clean()

        # Ensure the user address is part of the user group
        # associated with the payment method.
        if self.payment_method.user_group != self.user_address.user_group:
            raise ValidationError(
                "User address is not part of the user group associated "
                "with the payment method."
            )

    def is_default_payment_method(self):
        return self.user_address.default_payment_method == self.payment_method


@receiver(post_save, sender=PaymentMethodUserAddress)
def save_payment_method(sender, instance: PaymentMethodUserAddress, created, **kwargs):
    instance.payment_method.sync_stripe_payment_method(instance.user_address)

    # If this is the first PaymentMethod for this UserAddress,
    # set it as the default payment method.
    if created:
        instance.user_address.default_payment_method = instance.payment_method
        instance.user_address.save()


@receiver(pre_delete, sender=PaymentMethodUserAddress)
def delete_payment_method(sender, instance: PaymentMethodUserAddress, using, **kwargs):
    # Don't delete the UserAddress if it's the default payment method.
    if instance.is_default_payment_method():
        raise ValidationError(
            "Cannot delete this rrelationship. This PaymentMethod is "
            "the default for the UserAddress."
        )

    # Once there is a PaymentMethodUserAddress, don't let the UserAddress

    # Sync the Payment Method with Stripe.
    instance.payment_method.sync_stripe_payment_method(instance.user_address)
