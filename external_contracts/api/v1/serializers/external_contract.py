from rest_framework import serializers

from external_contracts.api.v1.serializers.external_contract_attachment import (
    ExternalContractAttachmentSerializer,
)
from external_contracts.models.external_contract import ExternalContract


class ExternalContractSerializer(serializers.ModelSerializer):
    external_contract_attachments = ExternalContractAttachmentSerializer(many=True)

    class Meta:
        model = ExternalContract
        fields = "__all__"
