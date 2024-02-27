from rest_framework import serializers

from api.serializers import UserAddressSerializer
from billing.models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    user_address = UserAddressSerializer()

    class Meta:
        model = Invoice
        fields = "__all__"
