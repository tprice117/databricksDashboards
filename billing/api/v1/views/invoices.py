from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.exceptions import (
    ValidationError as DRFValidationError,
)
from rest_framework.views import APIView

from common.utils.json_encoders import DecimalFloatEncoder
from billing.api.v1.serializers import InvoiceSerializer, InvoiceExpandedSerializer
from billing.models import Invoice
from api.models.order.order import Order


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


class OrderInvoiceView(APIView):
    """
    This class-based view returns an Invoice with line items for a Transaction.
    """

    @extend_schema(
        responses={
            200: InvoiceExpandedSerializer(many=True),
        },
    )
    def get(self, request, *args, **kwargs):
        """
        Returns:
          A list of Invoice Items that are related to this Transaction.
        """
        order_id = self.kwargs.get("order_id")
        if not order_id:
            raise DRFValidationError("Must pass in order_id")

        order = Order.objects.get(id=order_id)
        invoices = order.get_invoices()

        # Return CheckoutOrder serialized data.
        data = InvoiceExpandedSerializer(invoices, many=True).data

        return JsonResponse(data, encoder=DecimalFloatEncoder, safe=False)
