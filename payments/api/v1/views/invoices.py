import datetime

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view

from api.models.user.user_address import UserAddress
from api.serializers import UserAddressSerializer
from common.utils.stripe.stripe_utils import StripeUtils
from payments.api.v1.serializers.invoice import InvoiceSerializer


@csrf_exempt
@api_view(["GET"])
def invoices(request: HttpRequest):
    # Get all UserAddresses from the authenticated user.
    user_addresses = UserAddress.objects.filter(user_group=request.user.user_group)

    invoices = []
    for user_address in user_addresses:
        # Get all invoices from Stripe for the UserAddress.
        fetched_invoices = StripeUtils.Invoice.get_all(
            customer_id=user_address.stripe_customer_id,
        )

        # Add the invoices to the list of invoices.
        invoices.extend(
            [
                {
                    "id": invoice["id"],
                    "user_address": UserAddressSerializer(user_address).data,
                    "amount_due": invoice["amount_due"],
                    "amount_paid": invoice["amount_paid"],
                    "amount_remaining": invoice["amount_remaining"],
                    "due_date": (
                        datetime.datetime.fromtimestamp(
                            invoice["due_date"],
                        )
                        if invoice["due_date"]
                        else None
                    ),
                    "hosted_invoice_url": invoice["hosted_invoice_url"],
                    "invoice_pdf": invoice["invoice_pdf"],
                    "metadata": invoice["metadata"],
                    "number": invoice["number"],
                    "paid": invoice["paid"],
                    "status": invoice["status"],
                }
                for invoice in fetched_invoices
            ]
        )

    # print("Info3: ", invoices)
    # # Serialize the invoices and return them in the response.
    # serialized_invoices = InvoiceSerializer(invoices, many=True)

    # # Check if the serialized invoices are valid.
    # is_valid = serialized_invoices.is_valid()

    # return JsonResponse(
    #     (serialized_invoices.data if is_valid else serialized_invoices.errors),
    #     safe=False,
    #     status=200 if is_valid else 500,
    # )
    return JsonResponse(invoices, safe=False, status=200)
