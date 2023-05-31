from rest_framework import authentication
from rest_framework import exceptions
import requests

from api.utils import get_user_data
from .models import User, Goal, ConnectedItem, Account, Holding

class CustomAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        try:
            token = request.META.get('HTTP_AUTHORIZATION').replace("Bearer ", "")
            
            user_data = get_user_data(token)
            user = User.objects.get(user_id=user_data['user_id'])
            return (user, None)
        except Exception as ex:
            # Catch all other exceptions.
            raise exceptions.AuthenticationFailed('Not authenticated. ' + str(ex))


        