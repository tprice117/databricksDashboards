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
    customer_rate_decimal = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        help_text="The rate the customer is charged for this item (ex: 25.00)",
    )
    seller_rate_decimal = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        help_text="The rate the seller is paid for this item (ex: 20.00)",
    )

    # Making the 'quantity' field optional since the pre_save
    # signal will set the value of 'quantity' based on the value of
    # 'quantity_decimal'.
    quantity = models.IntegerField(
        blank=True,
    )
    customer_rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        help_text="The rate the customer is charged for this item (ex: 25.00)",
    )
    seller_rate = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        blank=True,
        help_text="The rate the seller is paid for this item (ex: 20.00)",
    )

    class Meta:
        verbose_name = "Transaction Material Fee"
        verbose_name_plural = "Transaction Material Fees"


@receiver(pre_save, sender=OrderMaterialFee)
def pre_save_order_material_fee(sender, instance: OrderMaterialFee, **kwargs):
    # Since the Stripe Invoice API requires 'quantity' to be an integer, we will
    # set the quantity to 1 if the quantity_decimal is not an whole number.
    if not instance.quantity_decimal % 1 == 0:
        # 'quantity_decimal' is a whole number. Set 'quantity' to the 'quantity_decimal'
        # value converted to an integer.
        instance.quantity = int(instance.quantity_decimal)
        instance.customer_rate = instance.customer_rate_decimal
        instance.seller_rate = instance.seller_rate_decimal
    else:
        # 'quantity_decimal' is not a whole number. Set 'quantity' to 1.
        instance.quantity = 1

        # Update customer_rate and seller_rate to be the total price of the material fee,
        # instead of the price per unit.
        instance.customer_rate = (
            instance.customer_rate_decimal * instance.quantity_decimal
        )
        instance.seller_rate = instance.seller_rate_decimal * instance.quantity_decimal
