"""Module of helper functions for sending internal emails.
"""

import mailchimp_transactional as MailchimpTransactional
from typing import Union
import requests
from django.conf import settings
from django.template.loader import render_to_string
from notifications.utils.add_email_to_queue import add_email_to_queue
from api.models import Order
import logging

logger = logging.getLogger(__name__)

mailchimp = MailchimpTransactional.Client(settings.MAILCHIMP_API_KEY)


def send_email_on_new_signup(
    email: str, created_by_downstream_team: bool = False
) -> Union[requests.Response, None]:
    """Send an email to the internal team when a new user signs up.

    Args:
        email: The email of the user who signed up.
        created_by_downstream_team: Whether the user was created by the Downstream team.

    Returns:
        The response from the Mailchimp API, or None if an error occurred.
    """
    try:
        # Send email to internal team.
        response = mailchimp.messages.send(
            {
                "message": {
                    "headers": {
                        "reply-to": email,
                    },
                    "from_name": "Downstream",
                    "from_email": "noreply@trydownstream.com",
                    "to": [{"email": "sales@trydownstream.com"}],
                    "subject": "New User App Signup",
                    "track_opens": True,
                    "track_clicks": True,
                    "text": "Woohoo! A new user signed up for the app. The email on their account is: ["
                    + email
                    + "]. This was created by: "
                    + ("[DOWNSTREAM TEAM]" if created_by_downstream_team else "[]")
                    + ".",
                }
            }
        )
        return response
    except Exception as e:
        logger.error(f"send_email_on_new_signup: [{e}]", exc_info=e)
        return None


def supplier_denied_order(order: Order) -> bool:
    """Send an email to the internal team when a supplier denies an order.

    Args:
        order: The Order object.

    Returns:
        True if successful or false if not.
    """
    try:
        subject = f"Supplier Denied Booking | seller: [{order.order_group.seller_product_seller_location.seller_product.seller.id}], order: [{order.id}]"
        # order.order_group.seller_product_seller_location.seller_product.seller.name
        html_content = render_to_string(
            "notifications/emails/supplier_email.min.html",
            {"order": order, "supplier_denied": True},
        )
        add_email_to_queue(
            from_email="dispatch@trydownstream.com",
            to_emails=["dispatch@trydownstream.com"],
            subject=subject,
            html_content=html_content,
            reply_to=order.order_group.seller_product_seller_location.seller_location.order_email,
        )
        return True
    except Exception as e:
        logger.error(f"supplier_denied_order: [order:{order.id}]-[{e}]", exc_info=e)
        return False
