import stripe
from rest_framework import serializers
from rest_framework.fields import JSONField

from payments.api.v1.serializers.invoice_status_transitions import (
    InvoiceStatusTransitionSerializer,
)
from payments.api.v1.serializers.transfer_data import TransferDataSerializer


class InvoiceSerializer(serializers.Serializer):
    # id = serializers.CharField(read_only=True)
    # object = serializers.CharField(read_only=True)
    # account_country = serializers.CharField(read_only=True)
    # account_name = serializers.CharField(read_only=True)
    # account_tax_ids = serializers.ListField(
    #     child=serializers.CharField(), read_only=True
    # )
    amount_due = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    amount_paid = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    amount_remaining = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    # # amount_shipping = serializers.IntegerField(read_only=True)
    # # application = serializers.CharField(read_only=True)
    # # application_fee_amount = serializers.IntegerField(read_only=True)
    # # attempt_count = serializers.IntegerField(read_only=True)
    # # attempted = serializers.BooleanField(read_only=True)
    # # auto_advance = serializers.BooleanField(read_only=True)
    # # automatic_tax = serializers.JSONField(read_only=True)
    # # billing_reason = serializers.CharField(read_only=True)
    # # charge = serializers.CharField(read_only=True)
    # # collection_method = serializers.CharField(read_only=True)
    # # created = serializers.IntegerField(read_only=True)
    # # currency = serializers.CharField(read_only=True)
    # # custom_fields = serializers.CharField(read_only=True)
    # # customer = serializers.CharField(read_only=True)
    # # customer_address = serializers.CharField(read_only=True)
    # # customer_email = serializers.EmailField(read_only=True)
    # # customer_name = serializers.CharField(read_only=True)
    # # customer_phone = serializers.CharField(read_only=True)
    # # customer_shipping = serializers.CharField(read_only=True)
    # # customer_tax_exempt = serializers.CharField(read_only=True)
    # # customer_tax_ids = serializers.ListField(
    # #     child=serializers.CharField(), read_only=True
    # # )
    # # default_payment_method = serializers.CharField(read_only=True)
    # # default_source = serializers.CharField(read_only=True)
    # # default_tax_rates = serializers.ListField(
    # #     child=serializers.CharField(), read_only=True
    # # )
    # description = serializers.CharField(
    #     read_only=True,
    #     allow_null=True,
    # )
    # # discount = serializers.CharField(read_only=True)
    # # discounts = serializers.ListField(
    # #     child=serializers.CharField(),
    # #     read_only=True,
    # #     allow_null=True,
    # # )
    # due_date = serializers.IntegerField(
    #     read_only=True,
    #     allow_null=True,
    # )
    # ending_balance = serializers.IntegerField(
    #     read_only=True,
    #     allow_null=True,
    # )
    # footer = serializers.CharField(
    #     read_only=True,
    #     allow_null=True,
    # )
    # # from_invoice = serializers.CharField(read_only=True)
    # hosted_invoice_url = serializers.CharField(
    #     read_only=True,
    #     allow_null=True,
    # )
    # invoice_pdf = serializers.CharField(
    #     read_only=True,
    #     allow_null=True,
    # )
    # # issuer = serializers.JSONField(read_only=True)
    # # last_finalization_error = serializers.CharField(read_only=True)
    # # latest_revision = serializers.CharField(
    # #     read_only=True,
    # #     allow_null=True,
    # # )
    # # lines = JSONField(read_only=True)
    # # livemode = serializers.BooleanField(read_only=True)
    # # metadata = JSONField(read_only=True)
    # # next_payment_attempt = serializers.IntegerField(read_only=True)
    # number = serializers.CharField(
    #     read_only=True,
    #     allow_null=True,
    # )
    # # on_behalf_of = serializers.CharField(read_only=True)
    # paid = serializers.BooleanField(read_only=True)
    # paid_out_of_band = serializers.BooleanField(read_only=True)
    # # payment_intent = serializers.CharField(read_only=True)
    # payment_settings = serializers.JSONField(read_only=True)
    # # period_end = serializers.IntegerField(read_only=True)
    # # period_start = serializers.IntegerField(read_only=True)
    # # post_payment_credit_notes_amount = serializers.IntegerField(read_only=True)
    # # pre_payment_credit_notes_amount = serializers.IntegerField(read_only=True)
    # # quote = serializers.CharField(
    # #     read_only=True,
    # #     allow_null=True,
    # # )
    # receipt_number = serializers.CharField(
    #     read_only=True,
    #     allow_null=True,
    # )
    # starting_balance = serializers.IntegerField(read_only=True)
    # statement_descriptor = serializers.CharField(
    #     read_only=True,
    #     allow_null=True,
    # )
    # status = serializers.CharField(read_only=True)
    # status_transitions = InvoiceStatusTransitionSerializer(read_only=True)
    # subscription = serializers.CharField(
    #     read_only=True,
    #     allow_null=True,
    # )
    # subtotal = serializers.IntegerField(read_only=True)
    # subtotal_excluding_tax = serializers.IntegerField(
    #     read_only=True,
    #     allow_null=True,
    # )
    # tax = serializers.IntegerField(
    #     read_only=True,
    #     allow_null=True,
    # )
    # total = serializers.IntegerField(read_only=True)
    # total_discount_amounts = serializers.ListField(
    #     child=serializers.JSONField(),
    #     read_only=True,
    #     allow_null=True,
    # )
    # total_excluding_tax = serializers.IntegerField(
    #     read_only=True,
    #     allow_null=True,
    # )
    # total_tax_amounts = serializers.ListField(
    #     child=serializers.JSONField(), read_only=True
    # )
    # transfer_data = TransferDataSerializer(
    #     read_only=True,
    #     allow_null=True,
    # )

    # def to_representation(self, value):
    #     print(value)
    #     # print(type(value))
    #     # # Assuming you have access to the stripe.Invoice object
    #     # invoice_data = value.to_dict()  # Convert stripe.Invoice object to a dictionary
    #     return super().to_representation(value)
