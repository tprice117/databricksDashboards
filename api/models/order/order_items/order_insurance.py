from api.models.order.common.order_item import OrderItem


class OrderInsurance(OrderItem):
    pass

    class Meta:
        verbose_name = "Transaction Insurance"
        verbose_name_plural = "Transaction Insurance"

    @staticmethod
    def update_order_insurance(order):
        """
        Utility method to update the OrderInsurance items in an Order.
        If the insurance amount is not equal to 15% of the order total,
        this method will create or update an OrderInsurance item to charge
        or refund the customer.
        """
        # Get the total of all of the OrderLineItems in the Order.
        order_total = order.customer_price()

        # Get 15% (currently hard-coded) of the order total.
        insurance_rate = 0.15
        new_insurance_amount = order_total * insurance_rate

        # Get the total of all OrderInsurance items in the Order.
        order_insurances = OrderInsurance.objects.filter(order=order)
        current_insurance_amount = sum(
            [order_insurance.customer_price for order_insurance in order_insurances],
            0,
        )

        # Calculate if there is a discrepancy between the total of all OrderInsurance
        # items in the Order and the 15% of the order total.
        difference = current_insurance_amount - new_insurance_amount

        # If there is a discrepancy, create/update a OrderInsurance item to charge or
        # refund the customer.
        # Either:
        # 1. If there is no existing OrderInsurance item with a
        #    stripe_invoice_line_item_id = None, create a new OrderInsurance item.
        # 2. If there is an existing OrderInsurance item with a
        #    stripe_invoice_line_item_id = None, update the customer_rate to the difference.

        if difference != 0:
            uninvoiced_order_insurance = order_insurances.filter(
                stripe_invoice_line_item_id=None,
            ).first()

            if uninvoiced_order_insurance:
                uninvoiced_order_insurance.customer_rate = difference
                uninvoiced_order_insurance.save()
            else:
                OrderInsurance.objects.create(
                    order=order,
                    quantity=1,
                    customer_rate=difference,
                    seller_rate=difference,
                    description=f"Insurance{'' if order_insurances.count() == 0 else ' (Adjustment)'}",
                )
