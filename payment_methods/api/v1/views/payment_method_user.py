from rest_framework import viewsets

from payment_methods.api.v1.serializers import PaymentMethodUserSerializer
from payment_methods.models import PaymentMethodUser


class PaymentMethodUserViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethodUser.objects.all()
    serializer_class = PaymentMethodUserSerializer
