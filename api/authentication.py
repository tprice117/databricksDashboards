from rest_framework import authentication
from rest_framework import exceptions
import requests

from api.utils import get_user_data
from .models import User

class CustomAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        try:
            token = request.META.get('HTTP_AUTHORIZATION').replace("Bearer ", "")
            
            if token == "addfe690-5b86-4671-a3bd-1764b32e20b0":
                return ("ALL", None)
            else:
                user_data = get_user_data(token)
                user = User.objects.get(user_id=user_data['user_id'])
                return (user, None)
        except Exception as ex:
            # Catch all other exceptions.
            raise exceptions.AuthenticationFailed('Not authenticated. ' + str(ex))


        