from rest_framework import serializers
from rest_framework.fields import JSONField


class TransferDataSerializer(serializers.Serializer):
    amount = serializers.IntegerField(
        read_only=True,
        allow_null=True,
    )
    destination = serializers.CharField(read_only=True)
