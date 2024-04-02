"""Lob API integration for sending physical checks to sellers. 
Docs: https://docs.lob.com/
Python lib: https://github.com/lob/lob-python
"""
import datetime
from django.utils import timezone
from typing import List, Union, Literal
import logging
import lob_python
from lob_python.api_client import ApiClient
from lob_python.api.checks_api import ChecksApi
from lob_python.api.bank_accounts_api import BankAccountsApi
from lob_python.api.postcards_api import PostcardsApi
from lob_python.model.bank_account_writable import BankAccountWritable, BankTypeEnum
from lob_python.model.check_editable import CheckEditable, ChkUseType
from lob_python.model.address_domestic import AddressDomestic
from lob_python.model.postcard_editable import PostcardEditable, PscUseType
from lob_python.model.address_editable import AddressEditable
from lob_python.model.merge_variables import MergeVariables
from lob_python.model.qr_code import QrCode

from django.conf import settings
from api.models import Order, Payout, SellerLocation, SellerInvoicePayable

logger = logging.getLogger("billing")


class Lob:

    def __init__(self):
        # Create check object.
        # Defining the host is optional and defaults to https://api.lob.com/v1
        # See configuration.py for a list of all supported configuration parameters.
        self.configuration = lob_python.Configuration(
            host=settings.LOB_API_HOST,
            username=settings.LOB_API_KEY,
        )
        self.from_address_id = "adr_4f5ca93c6bf5896b"
        self.bank_id = "bank_e83bd02ceb15448"

    def sendPhysicalCheck(
        self, seller_location: SellerLocation, amount, orders: List[Order], bank_id="bank_e83bd02ceb15448"
    ) -> int:
        """Sends a physical check to a seller. Returns check number on success or None on failure.
        Checks can't be sent internationally, country must be US.

        Args:
            seller_location (SellerLocation): _description_
            amount (_type_): _description_
            orders (List[Order]): _description_

        Returns:
            int: The check number on success or error raised on failure.
        """
        try:
            # Build remittance advice object.
            # Get SellerInvoicePayable
            seller_invoice_payable = SellerInvoicePayable.objects.filter(seller_location_id=seller_location.id).first()
            seller_invoice_str = "No Invoice Provided"
            if seller_invoice_payable:
                seller_invoice_str = seller_invoice_payable.supplier_invoice_id
            remittance_advice = []
            for order in orders:
                # Get total already paid to seller for this order.
                payouts = Payout.objects.filter(order=order)
                total_paid_to_seller = sum([payout.amount for payout in payouts])
                description = (
                    order.order_group.user_address.street
                    + " | "
                    + order.order_group.seller_product_seller_location.seller_product.product.main_product.name
                )

                remittance_advice.append(
                    {
                        "id": seller_invoice_str,
                        "amount": f"${float(order.seller_price() - total_paid_to_seller):.2f}",
                        "description": description[:64],
                        "date": order.end_date.strftime("%d/%m/%Y"),
                    }
                )

            # Convert date to datetime object.
            send_date = datetime.datetime.combine(order.end_date, datetime.time())
            now_date = timezone.now() + datetime.timedelta(hours=1)
            # If date is in the past, send check now.
            if send_date < datetime.datetime.now():
                send_date = now_date

            # https://docs.lob.com/#tag/Checks/operation/check_create
            check_editable = CheckEditable(
                description=description[:64],
                message=description[:64],
                bank_account=bank_id,
                amount=float(order.seller_price() - total_paid_to_seller),
                memo="rent",
                send_date=send_date,
                # logo = "https://s3-us-west-2.amazonaws.com/public.lob.com/assets/check_logo.png",
                # check_bottom = "<h1 style='padding-top:4in;'>Demo Check for {{name}}</h1>",
                # _from = "adr_210a8d4b0b76d77b",  # can use Lob address ID
                # 3245 Main Street, #235-434, Frisco, TX 75034
                _from=AddressDomestic(
                    name="Downstream",
                    address_line1="3245 Main Street",
                    address_line2="#235-434",
                    address_city="Frisco",
                    address_state="TX",
                    address_zip="75034",
                ),
                to=AddressDomestic(
                    name=seller_location.payee_name,
                    address_line1=seller_location.mailing_address.street,
                    address_line2="",
                    address_city=seller_location.mailing_address.city,
                    address_state=seller_location.mailing_address.state,
                    address_zip=seller_location.mailing_address.postal_code,
                ),
                # merge_variables = MergeVariables(name = "Harry",),
                use_type=ChkUseType('operational'),
                mail_type="usps_first_class"
            )

            with ApiClient(self.configuration) as api_client:
                api = ChecksApi(api_client)
                created_check = api.create(check_editable)
                return created_check  # ["check_number"]
        except lob_python.ApiException as e:
            # e.status = 400, reason, body
            # e.status 422, reason Unprocessable Entity
            print("Exception when calling ChecksApi->create: %s\n" % e)
            logger.error(f"Lob.sendPhysicalCheck.api: [{e}]", exc_info=e)
            raise
        except Exception as e:
            logger.error(f"Lob.sendPhysicalCheck: [{e}]", exc_info=e)
            raise

    def add_bank_account(
        self, description: str, routing_number: str, account_number: str, signatory: str,
        account_type: Union[Literal['company'], Literal['individual']] = 'company'
    ) -> str:
        """Add a bank account to Lob for sending checks.

        Args:
            description (str): An internal description that identifies this resource. Max of 255 characters.
            routing_number (str): The routing number of the bank account.
            account_number (str): The account number of the bank account.
            signatory (str): An account signer.
            account_type (str): The account type of the bank account 'company' OR 'individual'.

        Returns:
            str: The ID of the bank account.
        """
        try:
            bank_account_writable = BankAccountWritable(
                description=description,
                routing_number=routing_number,
                account_number=account_number,
                signatory=signatory,
                account_type=BankTypeEnum(account_type),
            )

            with ApiClient(self.configuration) as api_client:
                api = BankAccountsApi(api_client)
                created_bank_account = api.create(bank_account_writable)
                return created_bank_account
        except lob_python.ApiException as e:
            logger.error(f"Lob.add_bank_account.api: [{e}]", exc_info=e)
            raise
        except Exception as e:
            logger.error(f"Lob.add_bank_account: [{e}]", exc_info=e)
            raise

    def send_postcard(
        self, description: str, front: str, back: str, to: AddressEditable,
        merge_variables: MergeVariables = None,
        use_type: Union[Literal['marketing'], Literal['operational']] = 'marketing',
        qr_code: QrCode = None
    ):
        """Send a postcard to a recipient.
        API docs: https://docs.lob.com/#tag/Postcards/operation/postcard_create

        Args:
            description (str): A description that identifies this resource. Max of 255 characters.
            front (str): The front of the postcard.
            back (str): The back of the postcard.
            to (dict): The recipient's address.
            _from (dict): The sender's address.
            merge_variables (dict): The merge variables to be used in the postcard.
        """
        try:
            postcard_editable = PostcardEditable(
                description=description,
                front=front,
                back=back,
                to=to,
                _from=AddressEditable(
                    name="Downstream",
                    address_line1="3245 Main Street",
                    address_line2="#235-434",
                    address_city="Frisco",
                    address_state="TX",
                    address_zip="75034",
                ),
                use_type=PscUseType(use_type),
            )
            if merge_variables:
                postcard_editable.merge_variables = merge_variables
            if qr_code:
                postcard_editable.qr_code = qr_code

            with lob_python.ApiClient(self.configuration) as api_client:
                api = PostcardsApi(api_client)
                created_postcard = api.create(postcard_editable)
                print(created_postcard)
        except lob_python.ApiException as e:
            logger.error(f"Lob.send_postcard.api: [{e}]", exc_info=e)
            raise
        except Exception as e:
            logger.error(f"Lob.send_postcard: [{e}]", exc_info=e)
            raise
