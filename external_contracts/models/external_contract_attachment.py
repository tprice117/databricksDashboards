from django.db import models

from api.models import UserAddress
from common.models import BaseModel
from external_contracts.models.external_contract import ExternalContract


class ExternalContractAttachment(BaseModel):
    """
    This can be used to store attachments for an ExternalContract.
    """

    external_contract = models.ForeignKey(
        ExternalContract,
        models.CASCADE,
        related_name="external_contract_attachments",
    )
    file = models.FileField(
        upload_to="external_contract_attachments",
    )

    def __str__(self):
        return f"{self.external_contract.user_address.name} - {self.file.name}"
