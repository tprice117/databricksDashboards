from api.admin.inlines.order.order_items.common.order_item_inline import OrderItemInline
from api.models import OrderDamageFee


class OrderDamageFeeInline(OrderItemInline):
    model = OrderDamageFee
    show_change_link = True
    extra = 0
