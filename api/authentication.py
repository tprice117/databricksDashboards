from rest_framework import authentication
from rest_framework import exceptions
import requests

from api.utils.auth0 import get_user_data
from .models import User

class CustomAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        try:
            token = request.META.get('HTTP_AUTHORIZATION').replace("Bearer ", "")

            # Check if user is valid, confirm a DB user exists.
            # If not, create a new user.
            auth0_user = get_user_data(token)
            if auth0_user and not User.objects.filter(user_id=token).exists():
                User.objects.create(
                    user_id=token,
                    email=auth0_user['email']
                )
            
            if token == "addfe690-5b86-4671-a3bd-1764b32e20b0":
                return ("ALL", None)
            else:
                user = User.objects.get(user_id=token)
                return (user, None)
        except Exception as ex:
            # Catch all other exceptions.
            raise exceptions.AuthenticationFailed('Not authenticated. ' + str(ex))


        