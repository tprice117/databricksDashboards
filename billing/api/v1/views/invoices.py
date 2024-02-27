from rest_framework import viewsets

from billing.api.v1.serializers import InvoiceSerializer
from billing.models import Invoice


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        if self.request.user.user_group:
            return Invoice.objects.filter(
                user_address__user_group=self.request.user.user_group,
            )
        else:
            return Invoice.objects.filter(
                user_address__user=self.request.user,
            )
