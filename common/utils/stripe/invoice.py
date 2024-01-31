from typing import List

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class Invoice:
    @staticmethod
    def get_all():
        has_more = True
        starting_after = None
        data: List[stripe.Invoice] = []
        while has_more:
            invoices = stripe.Invoice.list(limit=100, starting_after=starting_after)
            data = data + invoices["data"]
            has_more = invoices["has_more"]
            starting_after = data[-1]["id"]
        return data

    @staticmethod
    def get(id: str):
        return stripe.Invoice.retrieve(id)

    @staticmethod
    def finalize(invoice_id: str):
        return stripe.Invoice.finalize_invoice(invoice_id)

    @staticmethod
    def attempt_pay(invoice_id: str):
        return stripe.Invoice.pay(invoice_id)
