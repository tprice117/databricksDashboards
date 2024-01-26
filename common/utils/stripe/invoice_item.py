import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class InvoiceItem:
    @staticmethod
    def get_all():
        has_more = True
        starting_after = None
        data = []
        while has_more:
            invoice_items = stripe.InvoiceItem.list(
                limit=100, starting_after=starting_after
            )
            data = data + invoice_items["data"]
            has_more = invoice_items["has_more"]
            starting_after = data[-1]["id"]
        return data

    @staticmethod
    def get(id: str):
        return stripe.InvoiceItem.retrieve(id)
