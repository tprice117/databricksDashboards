from api.admin.inlines.order.order_items.common.order_item_inline import OrderItemInline
from api.models import OrderPermitFee


class OrderPermitFeeInline(OrderItemInline):
    fields = [
        "permit",
    ] + OrderItemInline.fields

    model = OrderPermitFee
    show_change_link = True
    extra = 0
