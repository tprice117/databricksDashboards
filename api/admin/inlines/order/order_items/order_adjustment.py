from api.admin.inlines.order.order_items.common.order_item_inline import OrderItemInline
from api.models import OrderAdjustment


class OrderAdjustmentInline(OrderItemInline):
    model = OrderAdjustment
    show_change_link = True
    extra = 0
