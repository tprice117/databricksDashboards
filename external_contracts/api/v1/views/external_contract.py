from rest_framework import viewsets

from payment_methods.api.v1.serializers import PaymentMethodUserAddressSerializer
from payment_methods.models import PaymentMethodUserAddress


class PaymentMethodUserAddressViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethodUserAddress.objects.all()
    serializer_class = PaymentMethodUserAddressSerializer

    def get_queryset(self):
        return []
