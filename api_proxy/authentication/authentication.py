import logging
import uuid
import requests
import time
import json

import jwt
from django.core.exceptions import SuspiciousOperation
from django.urls import reverse
from mozilla_django_oidc.contrib.drf import OIDCAuthentication
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from mozilla_django_oidc.utils import absolutify
from requests.exceptions import HTTPError
from rest_framework import authentication, exceptions

from api.models.user.user import User

LOGGER = logging.getLogger(__name__)


class CustomOIDCAuthenticationBackend(OIDCAuthentication):
    """Custom OIDC authentication backend with admin token handling and impersonation."""

    def authenticate(self, request, **kwargs):
        """Authenticates a user based on the OIDC code flow, with additional checks for admin tokens and impersonation."""

        print("CustomOIDCAuthenticationBackend")
        # 1. Check for pre-defined admin tokens (stored securely)
        #  - This bypasses the OIDC flow for authorized admins.
        admin_tokens = [
            "addfe690-5b86-4671-a3bd-1764b32e20b0",
            "bce8c44e-d435-4686-8179-81e6dbd1da60",
        ]  # Replace with actual tokens (e.g., env variables)
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split()[1]
            if token in admin_tokens:
                # Consider returning a specific admin user object here
                # instead of "ALL" for better authorization control.
                LOGGER.info(f"Admin user authenticated with token {token}")
                return ("ALL", None)

        # 2. Delegate to OIDC authentication for regular users
        #  - If not an admin, use the standard OIDC flow for authentication.
        id_token = request.META.get("HTTP_X_AUTHORIZATION_ID_TOKEN")

        if not id_token:
            return None

        decoded_id_token = jwt.decode(id_token, None, None) if id_token else None

        # Check if the ID token contains the email field.
        if decoded_id_token and "email" in decoded_id_token:
            email = decoded_id_token["email"].casefold()

            # Get or create a user based on the email address.
            user = User.objects.filter(email__iexact=email)
            if user.exists():
                user = user.first()
                created = False
            else:
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "username": email,
                        "user_id": (
                            decoded_id_token["sub"]
                            if "sub" in decoded_id_token
                            else None
                        ),
                    },
                )
        else:
            return None

        if not user:
            msg = "Login failed: No user found for the given access token."
            raise exceptions.AuthenticationFailed(msg)

        # 3. Handle impersonation only for staff users with proper header
        #  - This allows staff users to act on behalf of other users.
        on_behalf_of_header = request.META.get("HTTP_X_ON_BEHALF_OF")
        if not on_behalf_of_header:
            return (user, None)
        else:
            # Check if the user is staff. If not, raise an exception.
            if not user.is_staff:
                raise SuspiciousOperation(
                    "Only staff users are allowed to impersonate other users.",
                )

            # Check if the 'X-ON-BEHALF-OF' header is a valid UUID.
            try:
                on_behalf_of_user_id = uuid.UUID(str(on_behalf_of_header))
            except ValueError:
                raise SuspiciousOperation(
                    "Invalid 'X-ON-BEHALF-OF' header format. Must be a valid UUID."
                )

            on_behalf_of_user = User.objects.get(pk=on_behalf_of_user_id)
            LOGGER.info(
                f"User '{user.username}' impersonates user '{on_behalf_of_user.username}'"
            )
            print(
                f"User '{user.username}' impersonates user '{on_behalf_of_user.username}'"
            )
            return (on_behalf_of_user, user)


class PortalOIDCAuthentication(OIDCAuthenticationBackend):
    """Override the OIDC authentication backend to handle caching the userinfo."""

    def get_userinfo(self, access_token, id_token, payload):
        """Return user details dictionary. The id_token and payload are not used in
        the default implementation, but may be used when overriding this method.
        NOTE: This method caches the userinfo in the session to avoid unnecessary requests,
        inorder to mitigate auth0 429 errors. This was one of the suggestions from auth0:
        https://community.auth0.com/t/userinfo-endpoint-returns-429-rate-limits-error/89210

        https://auth0.com/docs/troubleshoot/customer-support/operational-policies/rate-limit-policy
        In addition, there is a same user login rate limit: If one IP address makes 20 login
        attempts in one minute to the same user account, the rate limit comes into effect.
        After that, Auth0 allows the user 10 attempts per minute. Any combination of successful
        and failed login attempts count toward this limit.
        """

        session = self.request.session
        user_info = session.get("oidc_userinfo")
        user_info_expiration = session.get("oidc_userinfo_expiration")
        expiration_interval = 60 * 5  # 5 minutes
        if user_info_expiration and user_info_expiration > time.time():
            return json.loads(user_info)

        user_response = requests.get(
            self.OIDC_OP_USER_ENDPOINT,
            headers={"Authorization": "Bearer {0}".format(access_token)},
            verify=self.get_settings("OIDC_VERIFY_SSL", True),
            timeout=self.get_settings("OIDC_TIMEOUT", None),
            proxies=self.get_settings("OIDC_PROXY", None),
        )
        user_response.raise_for_status()
        session["oidc_userinfo"] = user_response.text
        session["oidc_userinfo_expiration"] = time.time() + expiration_interval
        session.save()
        return user_response.json()
