import requests
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class SummaryItems:
    @staticmethod
    def get_headers():
        return {
            "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
        }

    @staticmethod
    def get_all_for_invoice(invoice_id: str):
        stripe_invoice_summary_items_response = requests.get(
            f"https://api.stripe.com/v1/invoices/{invoice_id}/summary_items",
            headers={
                "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
            },
        )
        return stripe_invoice_summary_items_response.json()["data"]

    @staticmethod
    def get_or_create_by_description(
        invoice: stripe.Invoice, description: str, expanded_description: str
    ):
        # Get existing Stripe Invoice Summary Item(s) for this Invoice.
        stripe_invoice_summary_items = SummaryItems.get_all_for_invoice(invoice.id)

        # Ensure we have a Stripe Invoice Summary Item for this Invoice.
        # If order.stripe_invoice_summary_item_id is None, then create a new one.
        existing_item = next(
            (
                item
                for item in stripe_invoice_summary_items
                if item["description"] == description
                or item["description"] == expanded_description
            ),
            None,
        )
        if existing_item:
            return existing_item
        else:
            new_summary_invoice_summary_item_response = requests.post(
                f"https://api.stripe.com/v1/invoices/{invoice.id}/summary_items",
                headers=SummaryItems.get_headers(),
                data={
                    "description": description,
                },
            )
            return new_summary_invoice_summary_item_response.json()

    @staticmethod
    def add_invoice_item_to_summary_item(
        invoice: stripe.Invoice,
        invoice_item_id: str,
        invoice_summary_item_id: str,
    ):
        response = requests.post(
            f"https://api.stripe.com/v1/invoices/{invoice.id}/lines/{invoice_item_id}",
            headers=SummaryItems.get_headers(),
            data={
                "rendering[summary_item]": invoice_summary_item_id,
            },
        )

        # Return JSON response, if successful. Else, return Exception.
        return response.json() if response.status_code == 200 else Exception(response)
