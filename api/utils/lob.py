"""Lob API integration for sending physical checks to sellers. 
Docs: https://docs.lob.com/
Python lib: https://github.com/lob/lob-python
"""
import datetime
from django.utils import timezone
from typing import List, Union, Literal
from dataclasses import dataclass
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


@dataclass
class CheckRemittanceHTMLResponse():
    html: str
    description: str
    is_attachment: bool


def get_check_remittance_page_html(remittance_advice: List[str], top_padding="3.65") -> str:
    """Get the HTML for a single remittance advice page.

    Args:
        remittance_advice (List[str]): Remittance advice items.
        top_padding (str, optional): Padding to add to top of page. Defaults to "3.65".

    Returns:
        str: HTML for a single remittance advice page.
    """
    return f'''<div style="padding-top:{top_padding}in; padding-left: .12in; padding-right: .12in; font-family: Thicccboi,Arial,sans-serif; font-size: 11pt; width: 8.5in; height:11in;">
    <h2 style="text-align: center; font-size: 1.8em;">Remittance Advice</h2>
    <table style="border-collapse: separate; width: 100%; border-radius: 10px; border: solid #ddd 1px; padding: 3px;">
        <thead>
            <tr style="background-color: #038480; color: white;">
                <th style="text-align: left; border-left: none; padding: 7px;">Supplier ID</th>
                <th style="text-align: left; border-left: 1px solid #ddd; padding: 7px;">Amount</th>
                <th style="text-align: left; border-left: 1px solid #ddd; padding: 7px;">Description</th>
                <th style="text-align: left; border-left: 1px solid #ddd; padding: 7px;">Date</th>
            </tr>
        </thead>
        <tbody>
            {''.join(remittance_advice) if remittance_advice else '<td colspan="4">No orders found.</td>'}
        </tbody>
    </table>
    '''


def get_check_remittance_item_html(
    seller_invoice_id: str, total: str, description: str, end_date: str, line_background="#ffffff"
) -> str:
    """Get the HTML for a single remittance advice item.

    Args:
        seller_invoice_id (str): Seller invoice ID.
        total (str): Total amount to be paid to the seller.
        description (str): Description of the order.
        end_date (str): End date of the order.
        line_background (str, optional): HTML row line background. Defaults to "#ffffff".

    Returns:
        str: Complete HTML for a single remittance advice item.
    """
    return f'''<tr style="background-color: {line_background};">
            <td style="border-left: none; padding: 7px;">{seller_invoice_id}</td>
            <td style="border-left: 1px solid #ddd; padding: 7px;">{total}</td>
            <td style="border-left: 1px solid #ddd; padding: 7px;">{description[:64]} this is a long description</td>
            <td style="border-left: 1px solid #ddd; padding: 7px;">{end_date}</td></tr>
            '''


def get_check_remittance_html(seller_location: SellerLocation, orders: List[Order]) -> CheckRemittanceHTMLResponse:
    """Get the HTML for the remittance advice on the check. If there are more than 6 orders, the remittance advice
    will be an attachment. If there are 6 or fewer orders, the remittance advice will be added to the check bottom.
    check_bottom must conform to the size in this template:
    https://s3-us-west-2.amazonaws.com/public.lob.com/assets/templates/check_bottom_template.pdf

    Args:
        seller_location (SellerLocation): The seller location to include in the remittance advice.
        orders (List[Order]): The orders to include in the remittance advice.

    Returns:
        CheckRemittanceHTMLResponse: The HTML for the remittance advice. Boolean denotes if the
                                     remittance advice is an attachment or can be added to the check bottom.
                                     Description is the description of the last order in the remittance advice.
    """

    # Get SellerInvoicePayable
    seller_invoice_payable = SellerInvoicePayable.objects.filter(seller_location_id=seller_location.id).first()
    seller_invoice_str = "No Invoice Provided"
    if seller_invoice_payable:
        seller_invoice_str = seller_invoice_payable.supplier_invoice_id

    remittance_advice = []
    line_background = "#ffffff"
    description = ""

    remittance_advice_html = ""
    for i, order in enumerate(orders):
        # Get total already paid to seller for this order.
        payouts = Payout.objects.filter(order=order)
        total_paid_to_seller = sum([payout.amount for payout in payouts])
        description = (
            order.order_group.user_address.street
            + " | "
            + order.order_group.seller_product_seller_location.seller_product.product.main_product.name
        )

        remittance_advice.append(
            get_check_remittance_item_html(
                seller_invoice_str,
                f"${float(order.seller_price() - total_paid_to_seller):.2f}",
                description, order.end_date.strftime("%d/%m/%Y"),
                line_background=line_background
            )
        )
        line_background = "#ffffff" if line_background == "#e6fafa" else "#e6fafa"

        if i % 13 == 0 and i != 0:
            remittance_advice_html += get_check_remittance_page_html(remittance_advice, top_padding=".12")
            remittance_advice = []

    if len(orders) > 6:
        top_padding = ".12"
        is_attachment = True
    else:
        top_padding = "3.65"
        is_attachment = False
    # Add any remaining remittance advice items.
    if remittance_advice or remittance_advice_html == "":
        # If there are less than 6 orders, add padding to the top of the remittance advice because this
        # will be attached to the check bottom. If there are more than 6 orders, the remittance advice will
        # be a separate attachment, so do not add the padding.
        remittance_advice_html += get_check_remittance_page_html(remittance_advice, top_padding=top_padding)

    return CheckRemittanceHTMLResponse(
        html=remittance_advice_html, is_attachment=is_attachment, description=description
    )


class Lob:

    def __init__(
        self, from_address_id: str = None, bank_id: str = None, check_logo: str = None,
        default_download_app_qr: QrCode = None
    ):
        # Create check object.
        # Defining the host is optional and defaults to https://api.lob.com/v1
        # See configuration.py for a list of all supported configuration parameters.
        self.configuration = lob_python.Configuration(
            host=settings.LOB_API_HOST,
            username=settings.LOB_API_KEY,
        )
        self.from_address_id = from_address_id if from_address_id is not None else "adr_4f5ca93c6bf5896b"
        self.bank_id = bank_id if bank_id is not None else "bank_e83bd02ceb15448"
        self.check_logo = check_logo if check_logo is not None else "https://assets-global.website-files.com/632d7c6afd27f7e6217dc2a8/648e48a5fa7bd074602c6206_Downstream%20D%20-%20Dark-p-500.png"
        if default_download_app_qr is not None:
            self.default_download_app_qr = default_download_app_qr
        else:
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
            seller_location (SellerLocation): The seller location to send the check to.
            amount (_type_): The amount to send to the seller.
            orders (List[Order]): The orders to include in the remittance advice.

        Returns:
            int: The check number on success or error raised on failure.
        """
        try:
            # Build remittance advice object.
            check_remittance = get_check_remittance_html(seller_location, orders)
            if len(check_remittance.html) > 10000:
                raise ValueError("Check remittance advice html is too long.")

            description = f"{len(orders)} items - {check_remittance.description[:100]}"
            check_editable = CheckEditable(
                description=description,
                bank_account=bank_id,
                amount=float(amount),
                memo="Marketplace Bookings Payout",
                logo=self.check_logo,
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

            # Add Remittance Advice as an attachment if more than 6 orders.
            if check_remittance.is_attachment:
                check_editable.attachment = check_remittance.html
                check_editable.message = f'''Downstream Marketplace Bookings Payout. Check attachment for Remittance Advice for {len(orders)} items.'''
            else:
                # Only message or check_bottom can be used
                if check_remittance.html:
                    check_editable.check_bottom = check_remittance.html
                else:
                    check_editable.message = "Downstream Marketplace Bookings Payout"

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
                return created_postcard
        except lob_python.ApiException as e:
            logger.error(f"Lob.send_postcard.api: [{e}]", exc_info=e)
            raise
        except Exception as e:
            logger.error(f"Lob.send_postcard: [{e}]", exc_info=e)
            raise
