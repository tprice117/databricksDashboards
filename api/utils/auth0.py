from uuid import uuid4
from django.conf import settings
import requests
import mailchimp_transactional as MailchimpTransactional
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)


def get_auth0_access_token():
    # Get access_token.
    payload = {
        "client_id": settings.AUTH0_CLIENT_ID,
        "client_secret": settings.AUTH0_CLIENT_SECRET,
        "audience": "https://" + settings.AUTH0_DOMAIN + "/api/v2/",
        "grant_type": "client_credentials",
    }
    headers = {"content-type": "application/json"}
    response = requests.post(
        "https://" + settings.AUTH0_DOMAIN + "/oauth/token",
        json=payload,
        headers=headers,
        timeout=5,
    )
    return response.json()["access_token"]


def create_user(email: str):
    headers = {"authorization": "Bearer " + get_auth0_access_token()}
    response = requests.post(
        "https://" + settings.AUTH0_DOMAIN + "/api/v2/users",
        json={
            "email": email,
            "connection": "Username-Password-Authentication",
            "password": str(uuid4())[:12],
        },
        headers=headers,
        timeout=30,
    )
    return response.json()["user_id"] if "user_id" in response.json() else None


def get_user_data(user_id: str):
    headers = {"authorization": "Bearer " + get_auth0_access_token()}
    response = requests.get(
        "https://" + settings.AUTH0_DOMAIN + "/api/v2/users/" + user_id,
        headers=headers,
        timeout=30,
    )
    return response.json()


def get_user_from_email(email: str):
    headers = {"authorization": "Bearer " + get_auth0_access_token()}
    response = requests.get(
        "https://" + settings.AUTH0_DOMAIN + "/api/v2/users-by-email?email=" + email,
        headers=headers,
        timeout=30,
    )
    json = response.json()
    return json[0]["user_id"] if len(json) > 0 and "user_id" in json[0] else None


def delete_user(user_id: str):
    if user_id is not None:
        headers = {"authorization": "Bearer " + get_auth0_access_token()}
        requests.delete(
            "https://" + settings.AUTH0_DOMAIN + "/api/v2/users/" + user_id,
            headers=headers,
            timeout=30,
        )


def get_password_change_url(user_id: str):
    if user_id is not None:
        headers = {
            "Authorization": "Bearer " + get_auth0_access_token(),
            "Content-Type": "application/json",
        }

        response = requests.post(
            "https://" + settings.AUTH0_DOMAIN + "/api/v2/tickets/password-change",
            json={
                "result_url": "https://www.google.com",
                "user_id": user_id,
                "ttl_sec": 0,
                "mark_email_as_verified": True,
                "includeEmailInRedirect": True,
            },
            headers=headers,
            timeout=30,
        )

        # Return ticket url.
        return response.json()["ticket"]


def invite_user(user, reset_password=False):
    if user.user_id is not None:
        if user.redirect_url is not None:
            from api.utils.utils import encrypt_string

            password_change_url = f"{settings.DASHBOARD_BASE_URL}/register/account/?key={encrypt_string(str(user.id))}"
        else:
            password_change_url = get_password_change_url(user.user_id)

        # Send User Invite Email to user.
        try:
            mailchimp = MailchimpTransactional.Client(settings.MAILCHIMP_API_KEY)
            if reset_password:
                subject = "Reset your Downstream password"
                email_template = "user_reset_password_email.html"
            else:
                subject = "You've been invited to Downstream!"
                email_template = "user-invite-email.html"
            mailchimp.messages.send(
                {
                    "message": {
                        "headers": {
                            "reply-to": "support@trydownstream.com",
                        },
                        "from_name": "Downstream",
                        "from_email": "support@trydownstream.com",
                        "to": [
                            {"email": user.email},
                        ],
                        "subject": subject,
                        "track_opens": True,
                        "track_clicks": True,
                        "html": render_to_string(
                            email_template,
                            {
                                "user": user,
                                "url": password_change_url,
                            },
                        ),
                    }
                }
            )
        except Exception as e:
            print("An exception occurred.")
            print(e)
            logger.error(f"invite_user: [{e}]", exc_info=e)
