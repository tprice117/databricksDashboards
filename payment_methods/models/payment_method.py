from django.db import models

from api.models import User, UserGroup
from common.models import BaseModel
from payment_methods.utils import DSPaymentMethods


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
        return DSPaymentMethods.Tokens.get_card(self.token)
