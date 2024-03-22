from rest_framework import viewsets

from payment_methods.api.v1.serializers import PaymentMethodSerializer
from payment_methods.models import PaymentMethod, PaymentMethodUser


class PaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        if self.request.user == "ALL":
            return self.queryset
        else:
            # Either of the following are true:
            # 1. PaymentMethod.User is the same as the request.user
            # 2. PaymentMethodUser exists with the same user and PaymentMethod.
            payment_method_users = PaymentMethodUser.objects.filter(
                user=self.request.user,
            ).values_list("payment_method", flat=True)

            return (
                self.queryset.filter(user=self.request.user)
                | self.queryset.filter(id__in=payment_method_users)
            ).distinct()
