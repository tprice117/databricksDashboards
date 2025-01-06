import requests
import stripe
from django.conf import settings
import logging

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


class SummaryItems:
    @staticmethod
    def get_headers():
        return {
            "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
        }

    @staticmethod
    def get_all_for_invoice(invoice_id: str):
        """Returns a list of all summary items for a given invoice.
        This api is not documented in the Stripe API documentation.

        Args:
            invoice_id (str): Sripe Invoice ID

        Raises:
            Exception: Returns the response if the status code is not 200

        Returns:
            list: Returns a list of all line items for a given invoice.
        """
        ret_data = []
        stripe_data = {"has_more": True}

        # Add pagination for more than 100 items
        while stripe_data["has_more"]:
            params = {"limit": 100}
            if "data" in stripe_data:
                params["starting_after"] = stripe_data["data"][-1]["id"]

            stripe_response = requests.get(
                f"https://api.stripe.com/v1/invoices/{invoice_id}/summary_items",
                params=params,
                headers={
                    "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
                },
            )
            if stripe_response.status_code == 200:
                stripe_data = stripe_response.json()
                ret_data.extend(stripe_data["data"])
            else:
                raise Exception(stripe_response)

        return ret_data

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
            try:
                if description.find("|") == -1:
                    raise ValueError(f"Invalid description {description}")
                if expanded_description.find("|") == -1:
                    raise ValueError(
                        f"Invalid expanded_description {expanded_description}"
                    )
            except Exception as e:
                logger.error(
                    f"Error in get_or_create_by_description: [{invoice.id}]-[{e}]"
                )
            new_summary_invoice_summary_item_response = requests.post(
                f"https://api.stripe.com/v1/invoices/{invoice.id}/summary_items",
                headers=SummaryItems.get_headers(),
                data={
                    "description": expanded_description,
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
