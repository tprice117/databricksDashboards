from typing import TypedDict, List, Optional
from decimal import Decimal


class InvoiceItem(TypedDict):
    group_id: str
    id: str
    amount: Decimal
    amount_excluding_tax: Optional[Decimal]
    description: str
    order_line_item_id: Optional[str]


class InvoiceGroup(TypedDict):
    id: str
    description: str


class InvoiceResponse(TypedDict):
    items: List[InvoiceItem]
    groups: List[InvoiceGroup]
