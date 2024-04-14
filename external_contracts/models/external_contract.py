from django.db import models

from api.models import UserAddress
from common.models import BaseModel


class ExternalContract(BaseModel):
    """
    This represents an external contract that is associated with a UserAddress.
    A customer can use this feature to store information about their contracts
    with suppliers. In addition, theu can mark the contract as "intrested in saving"
    to indicate that they would like to save money on this contract.
    """

    user_address = models.ForeignKey(
        UserAddress,
        models.CASCADE,
    )
    supplier_name = models.CharField(
        max_length=255,
    )
    account_number = models.CharField(
        max_length=255,
    )
    renewal_date = models.DateField()
    expiration_date = models.DateField()

    def __str__(self):
        return (
            f"{self.user_address.name} - {self.supplier_name} - {self.account_number}"
        )
