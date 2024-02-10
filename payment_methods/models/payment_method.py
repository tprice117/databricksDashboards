import basistheory
from basistheory.api import tokens_api
from django.db import models

from api.models import User, UserGroup
from common.models import BaseModel

configuration = basistheory.Configuration(
    api_key="key_us_pvt_C2Q1Y1236YdqQDJwMkGqCc",
)


class PaymentMethod(BaseModel):
    token = models.CharField(max_length=255)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    user_group = models.ForeignKey(
        UserGroup,
        on_delete=models.CASCADE,
    )

    @property
    def card_number(self):
        response = self.get_card()
        return (
            response["data"]["number"]
            if response and "data" in response and "number" in response["data"]
            else None
        )

    @property
    def card_brand(self):
        response = self.get_card()
        return (
            response["data"]["brand"]
            if response and "data" in response and "brand" in response["data"]
            else None
        )

    @property
    def card_exp_month(self):
        response = self.get_card()
        return (
            response["data"]["expiration_month"]
            if response
            and "data" in response
            and "expiration_month" in response["data"]
            else None
        )

    @property
    def card_exp_year(self):
        response = self.get_card()
        return (
            response["data"]["expiration_year"]
            if response and "data" in response and "expiration_year" in response["data"]
            else None
        )

    def get_card(self):
        with basistheory.ApiClient(configuration) as api_client:
            # Create an instance of the token client
            token_client = tokens_api.TokensApi(api_client)

            try:
                return token_client.get_by_id(id=self.token)
            except basistheory.ApiException as e:
                print("Exception when calling TokensApi->get_by_id: %s\n" % e)
