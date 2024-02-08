from rest_framework import viewsets

from payment_methods.api.v1.serializers import PaymentMethodSerializer
from payment_methods.models import PaymentMethod


class PaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
