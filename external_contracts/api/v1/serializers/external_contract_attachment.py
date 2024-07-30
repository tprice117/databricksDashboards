from rest_framework import serializers

from external_contracts.models import ExternalContractAttachment


class ExternalContractAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalContractAttachment
        fields = "__all__"
