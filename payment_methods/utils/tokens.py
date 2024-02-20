import basistheory
from basistheory.api import tokens_api

from payment_methods.utils.basistheory_config import api_client_use_pci


class Tokens:
    @staticmethod
    def get_card(token: str):
        # Create an instance of the token client
        token_client = tokens_api.TokensApi(api_client_use_pci)

        try:
            return token_client.get_by_id(id=token)
        except basistheory.ApiException as e:
            print("Exception when calling TokensApi->get_by_id: %s\n" % e)
