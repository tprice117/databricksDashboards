from api.models import OrderLineItem


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
