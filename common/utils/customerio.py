import json
import requests

from django.conf import settings
from common.utils.json_encoders import DecimalFloatEncoder
import logging

logger = logging.getLogger(__name__)


def send_email(
    send_to: list,
    message_data: dict,
    subject: str,
    template_id: int,
):
    """This sends a transactional email via Customer.io.
    https://customer.io/docs/api/app/#operation/sendEmail
    https://customer.io/docs/journeys/liquid-tag-list/?version=latest
    """
    json_data = None
    try:
        data = {
            "transactional_message_id": template_id,
            "subject": subject,
            "message_data": message_data,
        }
        headers = {
            "Authorization": f"Bearer {settings.CUSTOMER_IO_API_KEY}",
            "Content-Type": "application/json",
        }
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
                f"[{response.status_code}]-[{template_id}]: Error sending {to_emails} [{resp_json['meta']['error']}]"
            )
            return False
        return True
    except Exception as e:
        logger.error(
            f"customerid.send_email:[{template_id}] Error sending {to_emails}-[{subject}]-[{json_data}]-[{str(e)}]"
        )

        return False
