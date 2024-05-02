from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import datetime
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
import logging

from api.models import (
    Order,
    Seller,
    Payout,
    Order,
    SellerInvoicePayable,
    SellerLocation,
    SellerInvoicePayableLineItem,
)
from api.utils.utils import decrypt_string

logger = logging.getLogger(__name__)


########################
# Page views
########################


@login_required(login_url="/admin/login/")
def index(request):
    seller = request.user.user_group.seller
    context = {}
    context["user"] = request.user
    context["seller"] = seller
    return render(request, "supplier_dashboard/index.html", context)


@login_required(login_url="/admin/login/")
def profile(request):
    seller = request.user.user_group.seller
    context = {}
    context["user"] = request.user
    context["seller"] = seller
    return render(request, "supplier_dashboard/profile.html", context)


@login_required(login_url="/admin/login/")
def bookings(request):
    seller = request.user.user_group.seller
    context = {}
    context["user"] = request.user
    context["seller"] = seller
    return render(request, "supplier_dashboard/bookings.html", context)


@login_required(login_url="/admin/login/")
def booking_detail(request, order_id):
    seller = request.user.user_group.seller
    context = {}
    context["user"] = request.user
    context["seller"] = seller
    order = Order.objects.filter(id=order_id)
    order = order.select_related(
        "order_group__seller_product_seller_location__seller_product__seller",
        "order_group__user_address",
        "order_group__user",
        "order_group__seller_product_seller_location__seller_product__product__main_product",
    )
    order = order.prefetch_related(
        "payouts", "seller_invoice_payable_line_items"
    ).first()
    context["order"] = order
    return render(request, "supplier_dashboard/booking_detail.html", context)


@login_required(login_url="/admin/login/")
def payouts(request):
    context = {}
    context["user"] = request.user
    # NOTE: Can add stuff to session if needed to speed up queries.
    # if not request.session.get("seller"):
    #     request.session["seller"] = request.user.user_group.seller
    context["seller"] = request.user.user_group.seller
    orders = Order.objects.filter(
        order_group__user_id=request.user.id
    ).prefetch_related("payouts")
    context["payouts"] = []
    for order in orders:
        context["payouts"].extend([p for p in order.payouts.all()])
    return render(request, "supplier_dashboard/payouts.html", context)


@login_required(login_url="/admin/login/")
def payout_detail(request, payout_id):
    # NOTE: Can add stuff to session if needed to speed up queries.
    payout = None
    if not payout:
        payout = Payout.objects.get(id=payout_id)
    context = {}
    context["user"] = request.user
    # context["seller"] = request.user.user_group.seller
    # TODO: Check if this is a checkbook payout (this changes with LOB integration).
    if payout.checkbook_payout_id:
        context["related_payouts"] = Payout.objects.filter(
            checkbook_payout_id=payout.checkbook_payout_id
        )
    context["payout"] = payout
    return render(request, "supplier_dashboard/payout_detail.html", context)


@login_required(login_url="/admin/login/")
def locations(request):
    seller = request.user.user_group.seller
    context = {}
    context["user"] = request.user
    context["seller"] = seller
    seller_locations = SellerLocation.objects.filter(seller_id=seller.id)
    context["seller_locations"] = seller_locations
    return render(request, "supplier_dashboard/locations.html", context)


@login_required(login_url="/admin/login/")
def location_detail(request, location_id):
    seller = request.user.user_group.seller
    context = {}
    context["user"] = request.user
    context["seller"] = seller
    seller_location = SellerLocation.objects.get(id=location_id)
    context["seller_location"] = seller_location
    orders = (
        Order.objects.filter(order_group__user_id=request.user.id)
        .prefetch_related("payouts")
        .order_by("-end_date")
    )
    context["orders"] = []
    context["payouts"] = []
    for order in orders:
        if (
            order.order_group.seller_product_seller_location.seller_location_id
            == location_id
        ):
            context["orders"].append(order)
        context["payouts"].extend([p for p in order.payouts.all()])
    return render(request, "supplier_dashboard/location_detail.html", context)


@login_required(login_url="/admin/login/")
def received_invoices(request):
    seller = request.user.user_group.seller
    context = {}
    context["user"] = request.user
    context["seller"] = seller
    invoices = SellerInvoicePayable.objects.filter(
        seller_location__seller_id=seller.id
    ).order_by("-invoice_date")
    context["seller_invoice_payables"] = invoices
    return render(request, "supplier_dashboard/received_invoices.html", context)


@login_required(login_url="/admin/login/")
def received_invoice_detail(request, invoice_id):
    seller = request.user.user_group.seller
    context = {}
    context["user"] = request.user
    context["seller"] = seller
    invoice = SellerInvoicePayable.objects.get(id=invoice_id)
    # invoice_line_items = invoice.seller_invoice_payable_line_items.all()
    invoice_line_items = SellerInvoicePayableLineItem.objects.filter(
        seller_invoice_payable_id=invoice_id
    )
    context["seller_invoice_payable"] = invoice
    context["seller_invoice_payable_line_items"] = invoice_line_items
    return render(request, "supplier_dashboard/received_invoice_detail.html", context)


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
