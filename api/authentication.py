from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import authentication, exceptions

from api.utils.auth0 import get_user_data

from .models import User
from notifications.utils.internal_email import send_email_on_new_signup


class CustomAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        try:
            if "HTTP_AUTHORIZATION" not in request.META:
                raise exceptions.AuthenticationFailed(
                    "Authentication credentials were not provided."
                )
            token = request.META.get("HTTP_AUTHORIZATION").replace("Bearer ", "")

            # Check if user is valid, confirm a DB user exists.
            # If not, create a new user.
            auth0_user = get_user_data(token)
            user_exists = User.objects.filter(user_id=token).exists()
            is_admin = (token == "addfe690-5b86-4671-a3bd-1764b32e20b0") or (
                token == "bce8c44e-d435-4686-8179-81e6dbd1da60"
            )

            if auth0_user and not user_exists and not is_admin:
                User.objects.create(
                    user_id=token,
                    email=auth0_user["email"],
                    first_name=(
                        auth0_user["first_name"] if "first_name" in auth0_user else None
                    ),
                    last_name=(
                        auth0_user["last_name"] if "last_name" in auth0_user else None
                    ),
                )
                # Send internal email to notify team.
                send_email_on_new_signup(self, created_by_downstream_team=False)

            if is_admin:
                return ("ALL", None)
            else:
                user = User.objects.get(user_id=token)
                return (user, None)
        except Exception as ex:
            # Catch all other exceptions.
            raise exceptions.AuthenticationFailed("Not authenticated. " + str(ex))


class CustomAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "api.authentication.CustomAuthentication"
    name = "CustomAuthentication"

    def get_security_definition(self, auto_schema):
        return {
            "type": "Auth0",
            "in": "header",
            "name": "Authorization",
            "description": 'Token-based authentication with required prefix "Bearer". Token is obtained from Auth0.',
        }
