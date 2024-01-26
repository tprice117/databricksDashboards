import requests
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class InvoiceLineItem:
    @staticmethod
    def get_all_for_invoice(invoice_id: str):
        stripe_invoice_items_response = requests.get(
            f"https://api.stripe.com/v1/invoices/{invoice_id}/lines",
            headers={
                "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
            },
        )

        return (
            stripe_invoice_items_response.json()["data"]
            if stripe_invoice_items_response.status_code == 200
            else Exception(stripe_invoice_items_response)
        )
