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


def send_push(
    template_id: int,
    email: str,
    to="all",
    title: str = None,
    message: str = None,
    custom_data: dict = None,
    message_data: dict = None,
    image_url: str = None,
    link: str = None,
):
    """This sends a transactional push to a user via Customer.io.
    https://docs.customer.io/api/app/#operation/sendPush

    Args:
        template_id (int): The Customer IO template ID of the push notification.
        email (str): A reference to the Customer IO profile.
        to (str, optional): The person's device(s) you want to send this push to. One of all, last_used,
                            or a device token (User.push_id). Defaults to "all".
        title (str): The title of the push notification. This overrides the title of the transactional template.
                     Defaults to None.
        message (str, optional): The message to be displayed in the push notification.
                                 This overrides the template message. Defaults to None.
        custom_data (dict, optional): Custom data to be sent with the push notification.
                                      Only supports string key value pairs. This overrides the title of the
                                      transactional template.Defaults to None.
        message_data (dict, optional): Key-value pairs referenced using liquid in your Customer IO template.
                                       Defaults to None.
        image_url (str, optional): The image to be displayed in the push notification. Defaults to None.
        link (str, optional): A deeplink or URL to redirect the user to.
                              This overrides the title of the transactional template. Defaults to None.

    Returns:
        bool: True if the push notification was sent successfully. False otherwise.
    """
    json_data = None
    try:
        data = {
            "transactional_message_id": template_id,
            "title": title,
            "message": message,
            "to": to,
            "identifiers": {"email": email},
        }
        if custom_data:
            data["custom_data"] = custom_data
        if message_data:
            data["message_data"] = message_data
        if image_url:
            data["image_url"] = image_url
        if link:
            data["link"] = link

        headers = {
            "Authorization": f"Bearer {settings.CUSTOMER_IO_API_KEY}",
            "Content-Type": "application/json",
        }

        json_data = json.dumps(data, cls=DecimalFloatEncoder)
        response = requests.post(
            "https://api.customer.io/v1/send/push",
            headers=headers,
            data=json_data,
        )
        if response.status_code >= 400:
            resp_json = response.json()
            logger.error(
                f"[{response.status_code}]-[{template_id}]: Error sending {email} [{resp_json['meta']['error']}]"
            )
            return False, resp_json["meta"]["error"]
        return True
    except Exception as e:
        logger.error(
            f"customerid.send_email:[{template_id}] Error sending {email}-[{title}]-[{json_data}]-[{str(e)}]"
        )

        return False, str(e)
