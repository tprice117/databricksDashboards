from django.shortcuts import render
import datetime
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
import logging

from api.models import Order, Seller
from api.utils.utils import decrypt_string

logger = logging.getLogger(__name__)


# Create your views here.


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def supplier_digest_dashboard(request, supplier_id, status: str = None):
    key = request.query_params.get("key", "")
    try:
        params = decrypt_string(key)
        if str(params) == str(supplier_id):
            context = {}
            non_pending_cutoff = datetime.date.today() - datetime.timedelta(days=15)
            if status:
                orders = Order.objects.filter(
                    order_group__seller_product_seller_location__seller_product__seller_id=supplier_id
                ).filter(status=status.upper())
                if status != Order.PENDING:
                    orders = orders.filter(end_date__gt=non_pending_cutoff)
                # Select related fields to reduce db queries.
                orders = orders.select_related(
                    "order_group__seller_product_seller_location__seller_product__seller",
                    "order_group__user_address",
                )
                orders = orders.order_by("-end_date")
                context["status"] = {
                    "name": status.upper(),
                    "orders": [
                        order for order in orders if order.end_date > non_pending_cutoff
                    ],
                }

                return render(
                    request,
                    "supplier_dashboard/snippets/accordian_status_orders.html",
                    context,
                )
            else:
                context["status_list"] = []
                supplier = Seller.objects.get(id=supplier_id)
                # NOTE: To include orders in this view, simply add them to the status_list.
                # orders = Order.objects.filter(
                #     order_group__seller_product_seller_location__seller_product__seller_id=supplier_id
                # ).filter(status=Order.PENDING)
                # # .filter(Q(status=Order.PENDING) | Q(status=Order.SCHEDULED))
                # # Select related fields to reduce db queries.
                # orders = orders.select_related(
                #     "order_group__seller_product_seller_location__seller_product__seller",
                #     "order_group__user_address",
                # ).order_by("-end_date")
                #
                # context["status_list"].append({"name": "PENDING", "orders": orders})
                context["seller"] = supplier
                context["status_complete_link"] = supplier.get_dashboard_status_url(
                    Order.COMPLETE
                )
                context["status_cancelled_link"] = supplier.get_dashboard_status_url(
                    Order.CANCELLED
                )
                context["status_scheduled_link"] = supplier.get_dashboard_status_url(
                    Order.SCHEDULED
                )
                context["status_pending_link"] = supplier.get_dashboard_status_url(
                    Order.PENDING
                )

                return render(request, "supplier_dashboard/dailydigest.html", context)
        else:
            raise ValueError("Invalid Token")
    except Exception as e:
        logger.error(f"supplier_digest_dashboard: [{e}]", exc_info=e)
        return render(
            request,
            "notifications/emails/failover_email_us.html",
            {"subject": f"Supplier%20Digest%20Error%20%5B{supplier_id}%5D"},
        )
