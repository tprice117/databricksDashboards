from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.exceptions import (
    APIException,
    ValidationError as DRFValidationError,
)
from rest_framework.views import APIView

from common.utils.json_encoders import DecimalFloatEncoder
from billing.api.v1.serializers import (
    InvoiceSerializer,
    InvoiceExpandedSerializer,
    PayInvoiceRequestSerializer,
    PayInvoiceResponseSerializer,
)
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


class PayInvoiceView(APIView):
    """
    This class-based view allows a user to pay an invoice.
    """

    @extend_schema(
        request=PayInvoiceRequestSerializer,
        responses={
            200: PayInvoiceResponseSerializer(),
        },
    )
    def post(self, request, *args, **kwargs):
        invoice_id = self.kwargs.get("invoice_id")
        # Convert request into serializer.
        serializer = PayInvoiceRequestSerializer(data=request.data)

        # Validate serializer.
        if not serializer.is_valid():
            raise APIException(serializer.errors)

        if not invoice_id:
            raise DRFValidationError("Must pass in invoice_id")

        invoice = Invoice.objects.get(id=invoice_id)
        payment_method = serializer.validated_data["payment_method"]
        try:
            is_paid = invoice.pay_invoice(payment_method)
            message = (
                "Invoice has been paid." if is_paid else "Invoice has not been paid."
            )
            # Return serialized data.
            data = PayInvoiceResponseSerializer(
                success=is_paid,
                message=message,
            ).data

            return JsonResponse(data, encoder=DecimalFloatEncoder, safe=False)
        except Exception as e:
            raise APIException(str(e))
