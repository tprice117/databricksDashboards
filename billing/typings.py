from typing import TypedDict, List, Optional
from decimal import Decimal
from datetime import date


class InvoiceItem(TypedDict):
    group_id: str
    id: str
    amount: Decimal
    amount_excluding_tax: Optional[Decimal]
    tax: Decimal
    description: str
    order_line_item_id: Optional[str]


class InvoiceGroup(TypedDict):
    id: str
    description: str


class InvoiceResponse(TypedDict):
    items: List[InvoiceItem]
    groups: List[InvoiceGroup]
    pre_payment_credit: Decimal
    post_payment_credit: Decimal


class InvoiceGroupedGroup(TypedDict):
    id: str
    description: str
    items: List[InvoiceItem]


class InvoiceGroupedResponse(TypedDict):
    groups: List[InvoiceGroupedGroup]
    pre_payment_credit: Decimal
    post_payment_credit: Decimal


class AccountSummaryInvoice(TypedDict):
    number: str
    invoice_due_date: Optional[date]
    invoice_status: str
    invoice_past_due: bool
    invoice_amount_due: Decimal


class AccountSummary(TypedDict):
    user_group_name: str
    total_invoices_not_paid_or_void: Decimal
    total_invoices_past_due: Decimal
    total_credit_limit_minus_total_balance: Decimal
    invoices: List[AccountSummaryInvoice]


class AccountPastDue(TypedDict):
    user_group_name: str
    total_past_due_30: Decimal
    total_past_due_31: Decimal
    total_past_due_61: Decimal
    invoices: List[AccountSummaryInvoice]
