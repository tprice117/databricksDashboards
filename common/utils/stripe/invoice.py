from typing import List

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class Invoice:
    @staticmethod
    def get_all(customer_id: str = None):
        has_more = True
        starting_after = None
        data: List[stripe.Invoice] = []
        while has_more:
            invoices = (
                stripe.Invoice.list(
                    limit=100,
                    starting_after=starting_after,
                    customer=customer_id,
                )
                if customer_id
                else stripe.Invoice.list(
                    limit=100,
                    starting_after=starting_after,
                )
            )

            data = data + list(invoice.to_dict() for invoice in invoices["data"])
            has_more = invoices["has_more"]
            print(f"has_more: {has_more}")
            print(f"len(data): {len(data)}")
            print(f"starting_after: {data[-1]['id']}" if has_more else "No more")
            starting_after = data[-1]["id"] if len(data) > 0 else None
        return data

    @staticmethod
    def get(id: str):
        return stripe.Invoice.retrieve(id)

    @staticmethod
    def finalize(invoice_id: str):
        return stripe.Invoice.finalize_invoice(invoice_id)

    @staticmethod
    def attempt_pay(invoice_id: str):
        try:
            invoice = stripe.Invoice.pay(invoice_id)
            return True if invoice.status == "paid" else False
        except:
            return False

    @staticmethod
    def send_invoice(invoice_id: str):
        return stripe.Invoice.send_invoice(invoice_id)
