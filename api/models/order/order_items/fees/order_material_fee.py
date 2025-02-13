from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from api.models.order.common.order_item import OrderItem


class OrderMaterialFee(OrderItem):
    order_line_item_type_code = "MATERIAL"

    # The 'quantity_decimal' field is used to store the quantity of the material fee
    # as a decimal number. This field is used to store the quantity as a decimal number
    # since the Stripe Invoice API requires the 'quantity' field to be an integer.
    quantity_decimal = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        help_text="The quantity of the material fee.",
    )
    # Making the 'quantity' field optional since the pre_save
    # signal will set the value of 'quantity' based on the value of
    # 'quantity_decimal'.
    quantity = models.IntegerField(
        blank=True,
    )

    rate_includes_quantity = models.BooleanField(
        default=False,
        help_text="Whether the rate includes the quantity or needs to be multiplied by the quantity.",
    )

    class Meta:
        verbose_name = "Transaction Material Fee"
        verbose_name_plural = "Transaction Material Fees"

    @property
    def customer_price(self):
        """
        The customer price is the customer rate times the quantity.
        Unless rate_includes_quantity is True, then the customer price is the total price of all the units.
        """
        if self.rate_includes_quantity:
            return self.customer_rate if self.customer_rate else None
        else:
            return (
                self.customer_rate * self.quantity
                if self.customer_rate and self.quantity
                else None
            )

    @property
    def seller_price(self):
        """
        The seller price is the seller rate times the quantity.
        Unless rate_includes_quantity is True, then the seller price is the total price of all the units.
        """
        if self.rate_includes_quantity:
            return self.seller_rate if self.seller_rate else None
        else:
            return (
                self.seller_rate * self.quantity
                if self.seller_rate and self.quantity
                else None
            )

    @property
    def platform_fee(self):
        """
        The platform fee is the difference between the customer rate and the seller rate.
        This is the amount the platform takes from the transaction in dollars.
        """
        if self.rate_includes_quantity:
            return (
                self.customer_rate - self.seller_rate
                if self.customer_rate and self.seller_rate
                else None
            )
        else:
            return (
                (self.customer_rate - self.seller_rate) * self.quantity
                if self.customer_rate and self.seller_rate
                else None
            )


@receiver(pre_save, sender=OrderMaterialFee)
def pre_save_order_material_fee(sender, instance: OrderMaterialFee, **kwargs):
    # Since the Stripe Invoice API requires 'quantity' to be an integer, we will
    # set the quantity to 1 if the quantity_decimal is not an whole number.
    # and price will include the quantity already.
    if not instance.quantity_decimal % 1 == 0:
        # 'quantity_decimal' is a whole number. Set 'quantity' to the 'quantity_decimal'
        # value converted to an integer.
        instance.quantity = int(instance.quantity_decimal)
        if instance.rate_includes_quantity:
            instance.rate_includes_quantity = False
            # Update customer_rate and seller_rate to be the price per unit
            instance.customer_rate = instance.customer_rate / instance.quantity
            instance.seller_rate = instance.seller_rate / instance.quantity
    else:
        # 'quantity_decimal' is not a whole number. Set 'quantity' to 1.
        instance.quantity = 1
        if not instance.rate_includes_quantity:
            instance.rate_includes_quantity = True
            # Update customer_rate and seller_rate to be the total price of all the units,
            # instead of the price per unit.
            instance.customer_rate = instance.customer_rate * instance.quantity_decimal
            instance.seller_rate = instance.seller_rate * instance.quantity_decimal
