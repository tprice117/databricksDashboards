from api.models import OrderLineItem
from api.models.order.common.order_item import OrderItem


def update_order_line_item_paid_status():
    # Get all order line items that have a stripe
    # invoice line item id and are not paid.
    order_line_items = OrderLineItem.objects.filter(
        stripe_invoice_line_item_id__isnull=False,
        paid=False,
    )

    # Loop through order line items.
    for order_line_item in order_line_items:
        # Get the Stripe Invoice for the Order Line Item.
        invoice = order_line_item.get_invoice()
        is_paid = invoice and invoice.status == "paid"

        # If the Stripe Invoice is paid, update the Order Line Item.
        # Once an Order Line Item is paid, it should not be updated again.
        if is_paid:
            order_line_item.paid = True
            order_line_item.save()

    # Next, do the same thing for all OrderItem subclasses.
    # Get all models that implement the OrderItem class.
    # This is a list of all OrderItem subclasses.
    order_item_models = OrderItem.__subclasses__()

    # Loop through all OrderItem subclasses.
    for order_item_model in order_item_models:
        # Get all OrderItems that have a stripe invoice line item id.
        order_items = order_item_model.objects.filter(
            stripe_invoice_line_item_id__isnull=False,
        )

        # Loop through OrderItems.
        for order_item in order_items:
            # Get the Stripe Invoice for the Order Item.
            invoice = order_item.get_invoice()
            is_paid = invoice and invoice.status == "paid"

            # If the Stripe Invoice is paid, update the Order Item.
            # Once an Order Item is paid, it should not be updated again.
            if is_paid:
                order_item.paid = True
                order_item.save()
