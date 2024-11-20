import json
import requests

from django.conf import settings
from common.utils.json_encoders import DecimalFloatEncoder
from billing.typings import AccountSummary
import logging

logger = logging.getLogger(__name__)


def send_consolidated_account_summary(send_to: list, account_summary: AccountSummary):
    """This is a new transactional email that will be sent to users who have opted in
    to receive account summary emails. This includes all users in a UserGroup as well as
    the billing email at the company.
    Trigger Logic: Every Monday when a UserGroup has a related invoice.status == “Open”
    """
    no_error = True
    try:
        data = {
            "transactional_message_id": 7,
            "subject": f"{account_summary['user_group_name']}'s Account Summary With Downstream Marketplace",
            "message_data": account_summary,
        }
        # https://customer.io/docs/api/app/#operation/sendEmail
        headers = {
            "Authorization": f"Bearer {settings.CUSTOMER_IO_API_KEY}",
            "Content-Type": "application/json",
        }
        # https://customer.io/docs/journeys/liquid-tag-list/?version=latest
        # send_to = ["mwickey@trydownstream.com"]
        to_emails = ",".join(send_to)
        data["to"] = to_emails
        data["identifiers"] = {"email": send_to[0]}

        json_data = json.dumps(data, cls=DecimalFloatEncoder)
        response = requests.post(
            "https://api.customer.io/v1/send/email",
            headers=headers,
            data=json_data,
        )
        if response.status_code >= 400:
            resp_json = response.json()
            logger.error(
                f"[{response.status_code}]: Error sending quote to {to_emails} [{resp_json['meta']['error']}]"
            )
    except Exception as e:
        no_error = False
        logger.error(
            f"Error sending quote to {to_emails}-[{account_summary['user_group_name']}]-[{str(e)}]"
        )

        return no_error
