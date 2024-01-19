from typing import List

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeUtils:
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

    class Customer:
        @staticmethod
        def create():
            return stripe.Customer.create()

        @staticmethod
        def get(id: str):
            return stripe.Customer.retrieve(id)

        @staticmethod
        def update(id: str, **kwargs):
            return stripe.Customer.modify(id, **kwargs)

    class Transfer:
        @staticmethod
        def create(**kwargs):
            return stripe.Transfer.create(**kwargs)
