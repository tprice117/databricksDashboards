"""Module of helper functions for sending internal emails."""

import mailchimp_transactional as MailchimpTransactional
from typing import Union
import requests
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
from notifications.utils.add_email_to_queue import add_email_to_queue
from api.models import Order
import logging

logger = logging.getLogger(__name__)

mailchimp = MailchimpTransactional.Client(settings.MAILCHIMP_API_KEY)


def send_email_on_new_signup(
    user, created_by_downstream_team: bool = False, message: str = None
) -> Union[requests.Response, None]:
    """Send a Teams message to the internal team when a new user signs up.
    Only sends if not created by the Downstream team.

    Args:
        User: The User who signed up.
        created_by_downstream_team: Whether the user was created by the Downstream team.

    Returns:
        The response from the Mailchimp API, or None if an error occurred.
    """
    try:
        if not created_by_downstream_team:
            # Send Teams Message to internal team.
            msg_body = f"Woohoo! A new user signed up for the app. The email on their account is: [{user.email}]."
            if message:
                msg_body += f"{message}"
            view_link = f"{settings.DASHBOARD_BASE_URL}{reverse('customer_user_detail', kwargs={'user_id': user.id})}"
            json_data = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": {
                            "type": "AdaptiveCard",
                            "version": "1.4",
                            "body": [
                                {
                                    "type": "TextBlock",
                                    "text": msg_body,
                                    "wrap": True,
                                },
                                {
                                    "type": "FactSet",
                                    "facts": [
                                        {"title": "Board:", "value": "Self Signup"},
                                        {
                                            "title": "Assigned to:",
                                            "value": "Sales Team",
                                        },
                                    ],
                                },
                            ],
                            "actions": [
                                {
                                    "type": "Action.OpenUrl",
                                    "title": "View",
                                    "url": view_link,
                                }
                            ],
                        },
                    }
                ],
            }
            # New Signups Channel on Teams
            team_link = "https://prod-48.westus.logic.azure.com:443/workflows/1b23a18cc97b4d99a35b2f09b7547cd2/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=gZ1nsGYvvrnDf3pzP5gNCI8gJ_937TAk6WVOzo6bSu0"
            response = requests.post(team_link, json=json_data)
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
