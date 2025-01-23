from api.admin.inlines.order.order_items.common.order_item_inline import OrderItemInline
from api.models import OrderPermitFee


class OrderPermitFeeInline(OrderItemInline):
    model = OrderPermitFee
    show_change_link = True
    extra = 0
    fields = [
        "permit",
    ] + OrderItemInline.fields
