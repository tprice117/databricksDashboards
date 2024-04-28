import logging
import uuid

from django.core.exceptions import SuspiciousOperation
from django.urls import reverse
from mozilla_django_oidc.contrib.drf import OIDCAuthentication
from mozilla_django_oidc.utils import absolutify

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
        print("Calling super().authenticate")
        user, token = super().authenticate(request, **kwargs)

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
