import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class InvoiceLineItem:
    @staticmethod
    def get_all_for_invoice(invoice_id: str):
        """Returns a list of all line items for a given invoice.
        https://docs.stripe.com/api/invoice-line-item/retrieve
        """
        has_more = True
        starting_after = None
        data = []
        while has_more:
            params = {"limit": 100}
            if starting_after:
                params["starting_after"] = starting_after
            invoice_items = stripe.Invoice.list_lines(invoice_id, **params)
            data.extend(invoice_items["data"])
            has_more = invoice_items["has_more"]
            if has_more:
                starting_after = data[-1]["id"]
        return data
