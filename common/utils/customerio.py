import json
import requests
import hashlib
import hmac
import binascii

from django.http import HttpResponse
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from customerio import analytics
from django.conf import settings
from common.utils.json_encoders import DecimalFloatEncoder
import logging

logger = logging.getLogger(__name__)

CUSTOMERIO_WHITE_LISTED_IPS = [
    "35.188.196.183",
    "104.198.177.219",
    "104.154.232.87",
    "130.211.229.195",
    "104.198.221.24",
    "104.197.27.15",
    "35.194.9.154",
    "104.154.144.51",
    "104.197.210.12",
    "35.225.6.73",
]


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
        (bool, string): True and delivery_id if the push notification was sent successfully.
                        False and error message otherwise.
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
        resp_json = response.json()
        return True, resp_json["delivery_id"]
    except Exception as e:
        logger.error(
            f"customerid.send_email:[{template_id}] Error sending {email}-[{title}]-[{json_data}]-[{str(e)}]"
        )

        return False, str(e)


def update_company(
    email: str,
    user_group_id: str,
    data: dict = None,
):
    """This creates/updates a company in Customer.io.
    https://docs.customer.io/cdp/sources/connections/servers/python/#group
    """
    try:
        analytics.write_key = settings.CUSTOMER_IO_TRACK_API_KEY
        analytics.host = "https://cdp.customer.io"

        # create or update company information
        # analytics.identify(email)
        analytics.group(email, user_group_id, data)
        analytics.flush()
        return True
    except Exception as e:
        logger.error(
            f"customerid.update_company:[Error updating company] Error sending [{email}]-[{user_group_id}]-[{data}]-[{str(e)}]"
        )

        return False


def update_person(
    email: str,
    data: dict = None,
):
    """This creates/updates a person in Customer.io.
    https://docs.customer.io/api/track/#tag/Track-Customers
    https://docs.customer.io/cdp/sources/connections/servers/python/#identify
    """
    try:
        analytics.write_key = settings.CUSTOMER_IO_TRACK_API_KEY
        analytics.host = "https://cdp.customer.io"

        # create or update person information
        analytics.identify(email, data)
        analytics.flush()
        return True
    except Exception as e:
        logger.error(
            f"customerid.update_person:[Error updating person] Error sending [{email}]-[{data}]-[{str(e)}]"
        )

        return False


def send_event(
    email: str,
    event_name: str,
    data: dict = None,
):
    """This sends an event to Customer.io.
    https://docs.customer.io/api/track/#operation/track
    https://docs.customer.io/cdp/sources/connections/servers/python/#track
    """
    try:
        analytics.write_key = settings.CUSTOMER_IO_TRACK_API_KEY
        analytics.host = "https://cdp.customer.io"

        # sample identify call usage:
        # ret = analytics.identify(email)
        # print("Identify Response:", ret)
        analytics.track(email, event_name, data)
        analytics.flush()
        return True
    except Exception as e:
        logger.error(
            f"customerid.send_event:[{event_name}] Error sending [{email}]-[{data}]-[{str(e)}]"
        )

        return False


def check_signature(
    webhook_signing_secret, xcio_signature, xcio_timestamp, request_body
):
    """
    Verifies the signature of a request.

    Args:
        webhook_signing_secret: The secret key used to sign the webhook request.
        xcio_signature: The signature provided in the request header (in hex format).
        xcio_timestamp: The timestamp provided in the request header.
        request_body: The raw request body as bytes.

    Returns:
        A tuple:
            - bool: True if the signature is valid, False otherwise.
            - error: None if signature is valid, or an Exception object if an error occurred.
    """
    try:
        signature = binascii.unhexlify(xcio_signature)
    except binascii.Error as e:
        return False, e

    mac = hmac.new(webhook_signing_secret.encode(), digestmod=hashlib.sha256)
    try:
        mac.update(f"v0:{xcio_timestamp}:".encode())
        mac.update(request_body)
    except Exception as e:
        return False, e

    computed_signature = mac.digest()

    if not hmac.compare_digest(computed_signature, signature):
        return False, None
    else:
        return True, None


@csrf_exempt
def customerio_webhook(request):
    """This processes a webhook event from Customer.io.
    https://customer.io/docs/api/webhooks/
    https://docs.customer.io/api/webhooks/#operation/reportingWebhook
    """
    try:
        from api.models import User
        from notifications.models import PushNotification, PushNotificationTo

        # Get requesting IP
        # REMOTE_ADDR: will be the load balancer, If using load balancer use HTTP_X_CLUSTER_CLIENT_IP
        ipaddress = request.META.get("HTTP_DO_CONNECTING_IP", "0.0.0.0")
        # remote_ip = request.META.get("HTTP_X_FORWARDED_FOR", None)
        if ipaddress not in CUSTOMERIO_WHITE_LISTED_IPS:
            logger.error(
                f"customerid.webhook:[Error processing webhook] Unauthorized IP [{ipaddress}]-[{request.META}]"
            )
            # return HttpResponse(status=401)

        # Example usage:
        webhook_secret = settings.CUSTOMER_IO_WEBHOOK_SIGNING_KEY
        signature_header = request.headers.get("X-CIO-Signature")
        timestamp_header = request.headers.get("X-CIO-Timestamp")
        request_data = request.body  # Use the actual request body

        is_valid, error = check_signature(
            webhook_secret, signature_header, timestamp_header, request_data
        )

        if not is_valid:
            logger.error(
                f"customerid.webhook:[Error processing webhook] Invalid signature [{signature_header}]-[{timestamp_header}]-[{error}]"
            )
            # return HttpResponse(status=401)
        # process event
        event = json.loads(request_data)
        logger.info(f"customerid.webhook:[{event}]")
        if event["object_type"] == "push":
            email = event["data"]["identifiers"]["email"]
            user = User.objects.filter(email=email).first()
            if not user:
                logger.error(
                    f"customerid.customerio_webhook:[Error processing webhook] User not found [{email}]"
                )
                return HttpResponse(status=200)
            # Update the PushNotification with the delivery_id.
            push_notification_to = PushNotificationTo.objects.filter(
                delivery_id=event["data"]["delivery_id"]
            )
            if push_notification_to.exists():
                push_notification_to = push_notification_to.first()
                if event["metric"] in ["clicked", "opened"]:
                    push_notification_to.read()
            else:
                with transaction.atomic():
                    # Create PushNotification and PushNotificationTo

                    template_id = event["data"].get("broadcast_id")
                    if not template_id:
                        template_id = event["data"].get("campaign_id")
                    if not template_id:
                        template_id = event["data"].get("newsletter_id")
                    if event["data"].get("content"):
                        content = json.loads(event["data"]["content"])
                        title = content["android"]["message"]["data"]["title"]
                        message = content["android"]["message"]["data"]["body"]
                        image = content["android"]["message"]["data"]["image"]
                        link = content["android"]["message"]["data"]["link"]
                        push_notification = PushNotification.objects.create(
                            title=title,
                            message=message,
                            template_id=template_id,
                            image=image,
                            link=link,
                            sent_at=timezone.make_aware(
                                timezone.datetime.fromtimestamp(event.get("timestamp"))
                            ),
                        )
                        push_notification_to = PushNotificationTo(
                            push_notification=push_notification,
                            user=user,
                            delivery_id=event["data"]["delivery_id"],
                        )
                        if event["metric"] in ["clicked", "opened"]:
                            push_notification_to.is_read = True
                            push_notification_to.read_at = timezone.now()
                        push_notification_to.save()
        return HttpResponse(status=200)
    except Exception as e:
        logger.error(
            f"customerid.customerio_webhook:[Error processing webhook] Error sending [{event}]-[{str(e)}]"
        )

        return HttpResponse(status=500)
