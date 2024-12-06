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

from notifications.utils.teams_message import send_teams_message

logger = logging.getLogger(__name__)

mailchimp = MailchimpTransactional.Client(settings.MAILCHIMP_API_KEY)


def send_new_signup_notification(
    user, created_by_downstream_team: bool = False, message: str = None
) -> Union[requests.Response, None]:
    """
    Send a Teams message to the internal team when a new user signs up.
    Only sends if not created by the Downstream team.

    Args:
        User: The User who signed up.
        created_by_downstream_team: Whether the user was created by the Downstream team.
        message: An optional message to include in the notification.

    Returns:
        The response from the Teams Webhook, or None if an error occurred.
    """
    try:
        if not created_by_downstream_team:
            # Send Teams Message to internal team.
            msg_body = f"Woohoo! A new user signed up for the app. The email on their account is: [{user.email}]."
            if message:
                msg_body += f"{message}"
            view_link = f"{settings.DASHBOARD_BASE_URL}{reverse('customer_user_detail', kwargs={'user_id': user.id})}"
            # New Signups Channel on Teams
            team_link = "https://prod-48.westus.logic.azure.com:443/workflows/1b23a18cc97b4d99a35b2f09b7547cd2/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=gZ1nsGYvvrnDf3pzP5gNCI8gJ_937TAk6WVOzo6bSu0"
            return send_teams_message(
                team_link=team_link,
                msg_body=msg_body,
                view_link=view_link,
                board="Self Signup",
                assigned_to="Sales Team",
            )
    except Exception as e:
        logger.error(f"send_new_signup_notification: [{e}]", exc_info=e)
        return None


def send_credit_application_notification(
    application,
    created_by_downstream_team: bool = False,
    message: str = None,
) -> Union[requests.Response, None]:
    """
    Send a Teams message to the internal team when a user submits a credit application.
    Only sends if not created by the Downstream team.

    Args:
        UserGroupCreditApplication: The UserGroupCreditApplication that was submitted.
        created_by_downstream_team: Whether the application was created by the Downstream team.
        message: An optional message to include in the notification.

    Returns:
        The response from the Teams Webhook, or None if an error occurred.
    """
    try:
        if not created_by_downstream_team:
            # Send Teams Message to internal team.
            msg_title = "New Credit Application Submission"
            msg_body = (
                f"We have a new credit application from {application.user_group.name}!"
            )
            if message:
                msg_body += f"{message}"
            custom_elements = [
                {
                    "type": "TextBlock",
                    "text": "Submitted by:",
                    "size": "large",
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {
                            "title": "Company:",
                            "value": application.user_group.name,
                        },
                        {
                            "title": "User:",
                            "value": application.created_by.email
                            if application.created_by
                            else f"N/A [application id: {application.id}]",
                        },
                    ],
                },
            ]
            if hasattr(application.user_group, "legal"):
                custom_elements.extend(
                    [
                        {
                            "type": "TextBlock",
                            "text": "Legal:",
                            "size": "large",
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {
                                    "title": "EIN:",
                                    "value": application.user_group.legal.tax_id
                                    or "N/A",
                                },
                                {
                                    "title": "Name:",
                                    "value": application.user_group.legal.name or "N/A",
                                },
                                {
                                    "title": "DBA:",
                                    "value": application.user_group.legal.doing_business_as
                                    or "N/A",
                                },
                                {
                                    "title": "Structure:",
                                    "value": application.user_group.legal.structure
                                    or "N/A",
                                },
                                {
                                    "title": "Industry:",
                                    "value": application.user_group.legal.industry
                                    or "N/A",
                                },
                                {
                                    "title": "Address:",
                                    "value": f"{application.user_group.legal.street}, {application.user_group.legal.city}, {application.user_group.legal.state} {application.user_group.legal.postal_code}"
                                    or "N/A",
                                },
                            ],
                        },
                    ]
                )
            # Credit Applications Channel on Teams
            team_link = "https://prod-125.westus.logic.azure.com:443/workflows/721cf2e120a1485787ca6594afe88b83/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=1m41ir1x72_6lDohTJLd3dlpl977l570fnV1xnsAFhg"
            return send_teams_message(
                team_link=team_link,
                msg_title=msg_title,
                msg_body=msg_body,
                board="Credit Applications",
                assigned_to="Ops Team",
                custom_elements=custom_elements,
                view_link=f"{settings.DASHBOARD_BASE_URL}/admin/api/usergroupcreditapplication/{application.id}",
            )
    except Exception as e:
        logger.error(f"send_credit_application_notification: [{e}]", exc_info=e)
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
