from django.db import models
from typing import Union

from common.models import BaseModel

LOB = None


def get_lob():
    """This function returns the Lob object. If the Lob object does not exist, it creates a new one.
    This just makes so Lob is not reinstatiated every time it is called.
    This also avoid the circular import issue."""
    global LOB
    if LOB is None:
        from api.utils.lob import Lob

        LOB = Lob()
    return LOB


class Payout(BaseModel):
    order = models.ForeignKey("api.Order", models.CASCADE, related_name="payouts")
    checkbook_payout_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_transfer_id = models.CharField(max_length=255, blank=True, null=True)
    lob_check_id = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)

    @property
    def is_check(self):
        """Returns True if the payout is a check (checkbookIO or Lob), False otherwise."""
        return True if self.lob_check_id or self.checkbook_payout_id else False

    def get_check(self):
        """Returns the check object from Lob if the payout is a check from Lob, None otherwise."""
        if self.lob_check_id:
            lob = get_lob()
            check = lob.get_check(self.lob_check_id)
            return check
        return None

    def invoice_id(self) -> Union[str, None]:
        """Get invoice_id from SellerInvoicePayableLineItem.seller_invoice_payable"""
        seller_invoice_payable_line_item = (
            self.order.seller_invoice_payable_line_items.all().first()
        )
        invoice_id = None
        if seller_invoice_payable_line_item:
            seller_invoice_payable = (
                seller_invoice_payable_line_item.seller_invoice_payable
            )
            if seller_invoice_payable:
                invoice_id = seller_invoice_payable.supplier_invoice_id
        return invoice_id
