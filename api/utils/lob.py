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
from lob_python.model.country_extended import CountryExtended
from lob_python.model.qr_code import QrCode

from django.conf import settings
from api.models import Order, Payout, SellerLocation, SellerInvoicePayable

logger = logging.getLogger("billing")


def get_check_remittance_html(seller_location: SellerLocation, orders: List[Order]) -> str:
    """Get the HTML for the remittance advice on the check.

    Args:
        orders (List[Order]): The orders to include in the remittance advice.

    Returns:
        str: The HTML for the remittance advice.
    """

    # Get SellerInvoicePayable
    seller_invoice_payable = SellerInvoicePayable.objects.filter(seller_location_id=seller_location.id).first()
    seller_invoice_str = "No Invoice Provided"
    if seller_invoice_payable:
        seller_invoice_str = seller_invoice_payable.supplier_invoice_id

    remittance_advice = []
    line_background = "#ffffff"
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
            f'''<tr style="background-color: {line_background};">
            <td style="border: 1px solid #ddd; padding: 5px;">{seller_invoice_str}</td>
            <td style="border: 1px solid #ddd; padding: 5px;">${float(order.seller_price() - total_paid_to_seller):.2f}</td>
            <td style="border: 1px solid #ddd; padding: 5px;">{description[:64]}</td>
            <td style="border: 1px solid #ddd; padding: 5px;">{order.end_date.strftime("%d/%m/%Y")}</td>
            </tr>'''
        )
        line_background = "#ffffff" if line_background == "#e6fafa" else "#e6fafa"

        remittance_advice.append(
            f'''<tr style="background-color: {line_background};">
            <td style="border: 1px solid #ddd; padding: 5px;">{seller_invoice_str}</td>
            <td style="border: 1px solid #ddd; padding: 5px;">${float(order.seller_price() - total_paid_to_seller):.2f}</td>
            <td style="border: 1px solid #ddd; padding: 5px;">{description[:64]}</td>
            <td style="border: 1px solid #ddd; padding: 5px;">{order.end_date.strftime("%d/%m/%Y")}</td>
            </tr>'''
        )

        line_background = "#ffffff" if line_background == "#e6fafa" else "#e6fafa"

        remittance_advice.append(
            f'''<tr style="background-color: {line_background};">
            <td style="border: 1px solid #ddd; padding: 5px;">{seller_invoice_str}</td>
            <td style="border: 1px solid #ddd; padding: 5px;">${float(order.seller_price() - total_paid_to_seller):.2f}</td>
            <td style="border: 1px solid #ddd; padding: 5px;">{description[:64]}</td>
            <td style="border: 1px solid #ddd; padding: 5px;">{order.end_date.strftime("%d/%m/%Y")}</td>
            </tr>'''
        )

        line_background = "#ffffff" if line_background == "#e6fafa" else "#e6fafa"

    remittance_html = f'''<div style="padding-top:3.65in; padding-left: .12in; padding-right: .12in; font-family: Thicccboi,Arial,sans-serif; font-size: 10pt;">
    <h2 style="text-align: center; font-size: 1.8em;">Remittance Advice</h2>
    <table style="border-collapse: collapse; width: 100%;">
        <thead>
            <tr style="background-color: #038480; color: white;">
                <th style="text-align: left; border: 1px solid #ddd; padding: 5px;">Supplier ID</th>
                <th style="text-align: left; border: 1px solid #ddd; padding: 5px;">Amount</th>
                <th style="text-align: left; border: 1px solid #ddd; padding: 5px;">Description</th>
                <th style="text-align: left; border: 1px solid #ddd; padding: 5px;">Date</th>
            </tr>
        </thead>
        <tbody>
            {''.join(remittance_advice) if remittance_advice else '<td colspan="4">No orders found.</td>'}
        </tbody>
    </table>
    </div>'''

    return remittance_html


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
        self.check_logo = "https://assets-global.website-files.com/632d7c6afd27f7e6217dc2a8/648e48a5fa7bd074602c6206_Downstream%20D%20-%20Dark-p-500.png"
        self.default_download_app_qr = QrCode(
            position="relative",
            redirect_url="https://trydownstream.onelink.me/sqsQ/b07f65lo",
            width="1",
            top=".12",
            right=".12",
            pages="back"  # pages="front,back" for both sides
        )

    def sendPhysicalCheck(
        self, seller_location: SellerLocation, amount: float, orders: List[Order], bank_id="bank_e83bd02ceb15448"
    ) -> int:
        """Sends a physical check to a seller. Returns check number on success or None on failure.
        Checks can't be sent internationally, country must be US.
        API Docs: https://docs.lob.com/#tag/Checks/operation/check_create

        Args:
            seller_location (SellerLocation): _description_
            amount (_type_): _description_
            orders (List[Order]): _description_

        Returns:
            int: The check number on success or error raised on failure.
        """
        try:
            # Build remittance advice object.
            check_bottom = get_check_remittance_html(seller_location, orders)

            for order in orders:
                # Get total already paid to seller for this order.
                description = (
                    order.order_group.user_address.street
                    + " | "
                    + order.order_group.seller_product_seller_location.seller_product.product.main_product.name
                )

            check_editable = CheckEditable(
                description=description[:64],
                bank_account=bank_id,
                amount=float(amount),
                memo="Marketplace Bookings Payout",
                logo=self.check_logo,
                # message="Downstream Marketplace Bookings Payout",  # Only message or check_bottom can be used
                check_bottom=check_bottom,
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
            else:
                postcard_editable.qr_code = self.default_download_app_qr

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
