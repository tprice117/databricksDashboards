from rest_framework import viewsets
from django.db.models import Q

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

            if self.request.user.user_group:
                # Allow api access to all payment methods for the Account.
                return self.queryset.filter(
                    user_group=self.request.user.user_group
                ).distinct()
            else:
                return self.queryset.filter(
                    Q(user=self.request.user) | Q(id__in=payment_method_users)
                ).distinct()
