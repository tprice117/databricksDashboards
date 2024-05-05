from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
import datetime
from itertools import chain
from django.http import HttpResponse, HttpResponseRedirect
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
    SellerInvoicePayable,
    SellerLocation,
    SellerInvoicePayableLineItem,
)
from api.utils.utils import decrypt_string
from notifications.utils import internal_email
from communications.intercom.utils.utils import get_json_safe_value
from .forms import UserForm, SellerForm, SellerCommunicationForm, SellerAboutUsForm

logger = logging.getLogger(__name__)


class InvalidFormError(Exception):
    """Exception raised for validation errors in the form."""

    def __init__(self, form, msg):
        self.form = form
        self.msg = msg

    def __str__(self):
        return self.msg


def to_dict(instance):
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields):
        data[f.name] = get_json_safe_value(f.value_from_object(instance))
    for f in opts.many_to_many:
        data[f.name] = [
            get_json_safe_value(i.id) for i in f.value_from_object(instance)
        ]
    return data


########################
# Page views
########################
# Add redirect to auth0 login if not logged in.
@login_required(login_url="/supplier/login/")
def supplier_login(request):
    pass


@login_required(login_url="/admin/login/")
def supplier_select(request):
    if request.method == "POST":
        seller_id = request.POST.get("seller_id")
    elif request.method == "GET":
        seller_id = request.GET.get("seller_id")
    else:
        return HttpResponse("Not Implemented", status=406)
    try:
        seller = Seller.objects.get(id=seller_id)
        request.session["seller"] = to_dict(seller)
        return HttpResponseRedirect("/supplier/")
    except Exception as e:
        return HttpResponse("Not Found", status=404)


@login_required(login_url="/admin/login/")
def index(request):
    context = {}
    context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    context["seller"] = request.session["seller"]
    return render(request, "supplier_dashboard/index.html", context)


@login_required(login_url="/admin/login/")
def profile(request):
    context = {}
    context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    context["seller"] = request.session["seller"]

    if request.method == "POST":
        form = UserForm(request.POST)
        context["form"] = form
        if form.is_valid():
            save_db = False
            if form.cleaned_data.get("first_name") != request.user.first_name:
                request.user.first_name = form.cleaned_data.get("first_name")
                save_db = True
            if form.cleaned_data.get("last_name") != request.user.last_name:
                request.user.last_name = form.cleaned_data.get("last_name")
                save_db = True
            if form.cleaned_data.get("phone") != request.user.phone:
                request.user.phone = form.cleaned_data.get("phone")
                save_db = True
            if form.cleaned_data.get("photo_url") != request.user.photo_url:
                request.user.photo_url = form.cleaned_data.get("photo_url")
                save_db = True
            if save_db:
                request.user.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            # return HttpResponse("", status=200)
            # This is an HTMX request, so respond with html snippet
            if request.headers.get("HX-Request"):
                return render(request, "supplier_dashboard/profile.html", context)
            else:
                return render(request, "supplier_dashboard/profile.html", context)
        else:
            # This will let bootstrap know to highlight the fields with errors.
            for field in form.errors:
                form[field].field.widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
    else:
        form = UserForm(
            initial={
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "phone": request.user.phone,
                "photo_url": request.user.photo_url,
                "email": request.user.email,
            }
        )
        context["form"] = form
    return render(request, "supplier_dashboard/profile.html", context)


@login_required(login_url="/admin/login/")
def company(request):
    context = {}
    context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    context["seller"] = request.session["seller"]
    if request.method == "POST":
        try:
            save_model = None
            if "company_submit" in request.POST:
                # Load other forms so template has complete data.
                seller_communication_form = SellerCommunicationForm(
                    initial={
                        "dispatch_email": request.user.user_group.seller.order_email,
                        "dispatch_phone": request.user.user_group.seller.order_phone,
                    }
                )
                context["seller_communication_form"] = seller_communication_form
                seller_about_us_form = SellerAboutUsForm(
                    initial={"about_us": request.user.user_group.seller.about_us}
                )
                context["seller_about_us_form"] = seller_about_us_form
                # Load the form that was submitted.
                form = SellerForm(request.POST)
                context["form"] = form
                if form.is_valid():
                    if (
                        form.cleaned_data.get("company_name")
                        != request.user.user_group.seller.name
                    ):
                        request.user.user_group.seller.name = form.cleaned_data.get(
                            "company_name"
                        )
                        save_model = request.user.user_group.seller
                    if (
                        form.cleaned_data.get("company_phone")
                        != request.user.user_group.seller.phone
                    ):
                        request.user.user_group.seller.phone = form.cleaned_data.get(
                            "company_phone"
                        )
                        save_model = request.user.user_group.seller
                    # if form.cleaned_data.get("first_name") != request.user.first_name:
                    #     request.user.first_name = form.cleaned_data.get("first_name")
                    #     save_model = request.user.user_group.seller
                    if (
                        form.cleaned_data.get("company_logo")
                        != request.user.user_group.seller.location_logo_url
                    ):
                        request.user.user_group.seller.location_logo_url = (
                            form.cleaned_data.get("company_logo")
                        )
                        save_model = request.user.user_group.seller
                else:
                    raise InvalidFormError(form, "Invalid SellerForm")
            elif "communication_submit" in request.POST:
                # Load other forms so template has complete data.
                form = SellerForm(
                    initial={
                        "company_name": request.user.user_group.seller.name,
                        "company_phone": request.user.user_group.seller.phone,
                        "first_name": request.user.first_name,
                        "company_logo": request.user.user_group.seller.location_logo_url,
                    }
                )
                context["form"] = form
                seller_about_us_form = SellerAboutUsForm(
                    initial={"about_us": request.user.user_group.seller.about_us}
                )
                context["seller_about_us_form"] = seller_about_us_form
                # Load the form that was submitted.
                seller_communication_form = SellerCommunicationForm(request.POST)
                context["seller_communication_form"] = seller_communication_form
                if seller_communication_form.is_valid():
                    save_model = None
                    if (
                        seller_communication_form.cleaned_data.get("dispatch_email")
                        != request.user.user_group.seller.order_email
                    ):
                        request.user.user_group.seller.order_email = (
                            seller_communication_form.cleaned_data.get("dispatch_email")
                        )
                        save_model = request.user.user_group.seller
                    if (
                        seller_communication_form.cleaned_data.get("dispatch_phone")
                        != request.user.user_group.seller.order_phone
                    ):
                        request.user.user_group.seller.order_phone = (
                            seller_communication_form.cleaned_data.get("dispatch_phone")
                        )
                        save_model = request.user.user_group.seller
                else:
                    raise InvalidFormError(
                        seller_communication_form, "Invalid SellerCommunicationForm"
                    )
            elif "about_us_submit" in request.POST:
                # Load other forms so template has complete data.
                form = SellerForm(
                    initial={
                        "company_name": request.user.user_group.seller.name,
                        "company_phone": request.user.user_group.seller.phone,
                        "first_name": request.user.first_name,
                        "company_logo": request.user.user_group.seller.location_logo_url,
                    }
                )
                context["form"] = form
                seller_communication_form = SellerCommunicationForm(
                    initial={
                        "dispatch_email": request.user.user_group.seller.order_email,
                        "dispatch_phone": request.user.user_group.seller.order_phone,
                    }
                )
                context["seller_communication_form"] = seller_communication_form
                # Load the form that was submitted.
                seller_about_us_form = SellerAboutUsForm(request.POST)
                context["seller_about_us_form"] = seller_about_us_form
                if seller_about_us_form.is_valid():
                    save_model = None
                    if (
                        seller_about_us_form.cleaned_data.get("about_us")
                        != request.user.user_group.seller.about_us
                    ):
                        request.user.user_group.seller.about_us = (
                            seller_about_us_form.cleaned_data.get("about_us")
                        )
                        save_model = request.user.user_group.seller
                else:
                    raise InvalidFormError(
                        seller_about_us_form, "Invalid SellerAboutUsForm"
                    )
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            # This is an HTMX request, so respond with html snippet
            if request.headers.get("HX-Request"):
                return render(
                    request, "supplier_dashboard/company_settings.html", context
                )
            else:
                return render(
                    request, "supplier_dashboard/company_settings.html", context
                )
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                e.form[field].field.widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
            # messages.error(request, e.msg)
    else:
        form = SellerForm(
            initial={
                "company_name": request.user.user_group.seller.name,
                "company_phone": request.user.user_group.seller.phone,
                "first_name": request.user.first_name,
                "company_logo": request.user.user_group.seller.location_logo_url,
            }
        )
        context["form"] = form
        seller_communication_form = SellerCommunicationForm(
            initial={
                "dispatch_email": request.user.user_group.seller.order_email,
                "dispatch_phone": request.user.user_group.seller.order_phone,
            }
        )
        context["seller_communication_form"] = seller_communication_form
        seller_about_us_form = SellerAboutUsForm(
            initial={"about_us": request.user.user_group.seller.about_us}
        )
        context["seller_about_us_form"] = seller_about_us_form
    return render(request, "supplier_dashboard/company_settings.html", context)


@login_required(login_url="/admin/login/")
def bookings(request):
    non_pending_cutoff = datetime.date.today() - datetime.timedelta(days=15)
    context = {}
    # context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    context["seller"] = request.session["seller"]
    seller = Seller.objects.get(id=context["seller"]["id"])
    orders = Order.objects.filter(
        order_group__seller_product_seller_location__seller_product__seller_id=context[
            "seller"
        ]["id"]
    )
    context["pending_count"] = 0
    context["scheduled_count"] = 0
    context["complete_count"] = 0
    context["cancelled_count"] = 0
    for order in orders:
        if order.status == Order.PENDING:
            context["pending_count"] += 1
        elif order.end_date > non_pending_cutoff:
            if order.status == Order.SCHEDULED:
                context["scheduled_count"] += 1
            elif order.status == Order.COMPLETE:
                context["complete_count"] += 1
            elif order.status == Order.CANCELLED:
                context["cancelled_count"] += 1
    context["status_complete_link"] = seller.get_dashboard_status_url(
        Order.COMPLETE, snippet_name="table_status_orders"
    )
    context["status_cancelled_link"] = seller.get_dashboard_status_url(
        Order.CANCELLED, snippet_name="table_status_orders"
    )
    context["status_scheduled_link"] = seller.get_dashboard_status_url(
        Order.SCHEDULED, snippet_name="table_status_orders"
    )
    context["status_pending_link"] = seller.get_dashboard_status_url(
        Order.PENDING, snippet_name="table_status_orders"
    )
    print(context["status_pending_link"])
    return render(request, "supplier_dashboard/bookings.html", context)


@login_required(login_url="/admin/login/")
def update_order_status(request, order_id, accept=True):
    context = {}
    try:
        order = Order.objects.get(id=order_id)
        context["order"] = order
        if order.status == Order.PENDING:
            if accept:
                order.status = Order.SCHEDULED
                order.save()
                if request.session.get("seller"):
                    seller_id = request.session["seller"]["id"]
                else:
                    seller_id = (
                        order.order_group.seller_product_seller_location.seller_product.seller_id
                    )
                request.session["seller"] = to_dict(request.user.user_group.seller)
                context["seller"] = request.session["seller"]
                non_pending_cutoff = datetime.date.today() - datetime.timedelta(days=15)
                orders = (
                    Order.objects.filter(
                        order_group__seller_product_seller_location__seller_product__seller_id=seller_id
                    )
                    .filter(status=Order.SCHEDULED)
                    .filter(end_date__gt=non_pending_cutoff)
                )
                orders = Order.objects.filter(
                    order_group__seller_product_seller_location__seller_product__seller_id=seller_id
                )
                # orders = orders.filter(Q(status=Order.SCHEDULED) | Q(status=Order.PENDING))
                pending_count = 0
                scheduled_count = 0
                complete_count = 0
                cancelled_count = 0
                for order in orders:
                    if order.status == Order.PENDING:
                        pending_count += 1
                    elif order.end_date > non_pending_cutoff:
                        if order.status == Order.SCHEDULED:
                            scheduled_count += 1
                        elif order.status == Order.COMPLETE:
                            complete_count += 1
                        elif order.status == Order.CANCELLED:
                            cancelled_count += 1
                context[
                    "oob_html"
                ] = f"""
                <span id="pending-count-badge" hx-swap-oob="true">{pending_count}</span>
                <span id="scheduled-count-badge" hx-swap-oob="true">{scheduled_count}</span>
                <span id="complete-count-badge" hx-swap-oob="true">{complete_count}</span>
                <span id="cancelled-count-badge" hx-swap-oob="true">{cancelled_count}</span>
                """
            else:
                # Send internal email to notify of denial.
                internal_email.supplier_denied_order(order)
    except Exception as e:
        logger.error(f"update_order_status: [{e}]", exc_info=e)
        return render(
            request,
            "notifications/emails/failover_email_us.html",
            {"subject": f"Supplier%20Approved%20%5B{order_id}%5D"},
        )
    if request.method == "POST":
        # if request.headers.get("HX-Request"): # This is an HTMX request, so respond with html snippet
        context["forloop"] = {"counter": request.POST.get("loopcount", 0)}
        return render(
            request,
            "supplier_dashboard/snippets/table_row_order_update.html",
            context,
        )
    else:
        # This is a GET request, so render a full success page.
        return render(
            request,
            "notifications/emails/supplier_order_updated.html",
            {"order_id": order_id},
        )


@login_required(login_url="/admin/login/")
def booking_detail(request, order_id):
    context = {}
    # context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
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
    # context["user"] = request.user
    # NOTE: Can add stuff to session if needed to speed up queries.
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
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
    context = {}
    # context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    seller_locations = SellerLocation.objects.filter(
        seller_id=request.session["seller"]["id"]
    )
    context["seller_locations"] = seller_locations
    return render(request, "supplier_dashboard/locations.html", context)


@login_required(login_url="/admin/login/")
def location_detail(request, location_id):
    context = {}
    # context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
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
    context = {}
    # context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
    invoices = SellerInvoicePayable.objects.filter(
        seller_location__seller_id=request.session["seller"]["id"]
    ).order_by("-invoice_date")
    context["seller_invoice_payables"] = invoices
    return render(request, "supplier_dashboard/received_invoices.html", context)


@login_required(login_url="/admin/login/")
def received_invoice_detail(request, invoice_id):
    context = {}
    # context["user"] = request.user
    if not request.session.get("seller"):
        request.session["seller"] = to_dict(request.user.user_group.seller)
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
    snippet_name = request.query_params.get("snippet_name", "accordian_status_orders")
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
                    f"supplier_dashboard/snippets/{snippet_name}.html",
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
