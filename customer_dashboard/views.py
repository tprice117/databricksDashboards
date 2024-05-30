from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from typing import List
import ast
import json
import uuid
from django.contrib import messages
from django.contrib.auth import logout
import datetime
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.urls import reverse
from api.pricing_ml import pricing
import logging

from api.models import (
    User,
    UserAddress,
    UserAddressType,
    Order,
    Subscription,
    OrderGroup,
    MainProductCategory,
    MainProduct,
    MainProductInfo,
    MainProductAddOn,
    MainProductCategoryInfo,
    MainProductServiceRecurringFrequency,
    MainProductWasteType,
    Product,
    AddOn,
    ProductAddOnChoice,
    SellerProductSellerLocation,
    SellerProduct,
    SellerLocation,
    ServiceRecurringFrequency,
)
from billing.models import Invoice
from api.utils.utils import decrypt_string
from notifications.utils import internal_email
from communications.intercom.utils.utils import get_json_safe_value

from .forms import UserForm, AccessDetailsForm, PlacementDetailsForm, UserAddressForm

logger = logging.getLogger(__name__)


class InvalidFormError(Exception):
    """Exception raised for validation errors in the form."""

    def __init__(self, form, msg):
        self.form = form
        self.msg = msg

    def __str__(self):
        return self.msg


def get_dashboard_chart_data(data_by_month: List[int]):
    # Create a list of labels along with earnings data of months going back from the current month to 8 months ago.
    data = []
    all_months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    current_month = datetime.date.today().month
    months = []
    for i in range(8, 1, -1):
        months.append(all_months[(current_month - i - 1) % 12])
        data.append(round(data_by_month[(current_month - i - 1) % 12], 2))

    dashboard_chart = {
        "type": "line",
        "data": {
            "labels": months,
            "datasets": [
                {
                    "label": "Earnings",
                    "fill": True,
                    "data": data,
                    "backgroundColor": "rgba(78, 115, 223, 0.05)",
                    "borderColor": "rgba(78, 115, 223, 1)",
                }
            ],
        },
        "options": {
            "maintainAspectRatio": False,
            "legend": {"display": False, "labels": {"fontStyle": "normal"}},
            "title": {"fontStyle": "normal"},
            "scales": {
                "xAxes": [
                    {
                        "gridLines": {
                            "color": "rgb(234, 236, 244)",
                            "zeroLineColor": "rgb(234, 236, 244)",
                            "drawBorder": False,
                            "drawTicks": False,
                            "borderDash": ["2"],
                            "zeroLineBorderDash": ["2"],
                            "drawOnChartArea": False,
                        },
                        "ticks": {
                            "fontColor": "#858796",
                            "fontStyle": "normal",
                            "padding": 20,
                        },
                    }
                ],
                "yAxes": [
                    {
                        "gridLines": {
                            "color": "rgb(234, 236, 244)",
                            "zeroLineColor": "rgb(234, 236, 244)",
                            "drawBorder": False,
                            "drawTicks": False,
                            "borderDash": ["2"],
                            "zeroLineBorderDash": ["2"],
                        },
                        "ticks": {
                            "fontColor": "#858796",
                            "fontStyle": "normal",
                            "padding": 20,
                        },
                    }
                ],
            },
        },
    }
    return dashboard_chart


def get_user(request: HttpRequest) -> User:
    """Returns the current user. This handles the case where the user is impersonating another user.

    Args:
        request (HttpRequest): Current request object.

    Returns:
        dict: Dictionary of the User object.
    """
    if request.session.get("user_id") and request.session.get("user_id") != str(
        request.user.id
    ):
        user = User.objects.get(id=request.session.get("user_id"))
    else:
        user = request.user
    return user


########################
# Page views
########################
# Add redirect to auth0 login if not logged in.
def customer_logout(request):
    logout(request)
    # Redirect to a success page.
    return HttpResponseRedirect("https://trydownstream.com/")


@login_required(login_url="/admin/login/")
def customer_search(request):
    context = {}
    if request.method == "POST":
        search = request.POST.get("search")
        try:
            user_id = uuid.UUID(search)
            users = User.objects.filter(id=user_id)
        except ValueError:
            users = User.objects.filter(email__icontains=search)
        context["users"] = users

    return render(request, "customer_dashboard/snippets/user_search_list.html", context)


@login_required(login_url="/admin/login/")
def customer_impersonation_start(request):
    if request.user.is_staff:
        if request.method == "POST":
            user_id = request.POST.get("user_id")
        elif request.method == "GET":
            user_id = request.GET.get("user_id")
        else:
            return HttpResponse("Not Implemented", status=406)
        try:
            user = User.objects.get(id=user_id)
            request.session["user_id"] = get_json_safe_value(user_id)
            return HttpResponseRedirect("/customer/")
        except Exception as e:
            return HttpResponse("Not Found", status=404)
    else:
        return HttpResponse("Unauthorized", status=401)


@login_required(login_url="/admin/login/")
def customer_impersonation_stop(request):
    del request.session["user_id"]
    return HttpResponseRedirect("/customer/")


@login_required(login_url="/admin/login/")
def index(request):
    context = {}
    context["user"] = get_user(request)
    orders = Order.objects.filter(order_group__user_id=context["user"].id)
    orders = orders.select_related(
        "order_group__seller_product_seller_location__seller_product__seller",
        "order_group__user_address",
        "order_group__user",
        "order_group__seller_product_seller_location__seller_product__product__main_product",
    )
    orders = orders.prefetch_related("payouts", "order_line_items")
    # .filter(status=Order.PENDING)
    context["earnings"] = 0
    earnings_by_category = {}
    pending_count = 0
    scheduled_count = 0
    complete_count = 0
    cancelled_count = 0
    earnings_by_month = [0] * 12
    for order in orders:
        context["earnings"] += float(order.customer_price())
        earnings_by_month[order.end_date.month - 1] += float(order.customer_price())

        category = (
            order.order_group.seller_product_seller_location.seller_product.product.main_product.main_product_category.name
        )
        if category not in earnings_by_category:
            earnings_by_category[category] = {"amount": 0, "percent": 0}
        earnings_by_category[category]["amount"] += float(order.customer_price())

        if order.status == Order.PENDING:
            pending_count += 1
        elif order.status == Order.SCHEDULED:
            scheduled_count += 1
        elif order.status == Order.COMPLETE:
            complete_count += 1
        elif order.status == Order.CANCELLED:
            cancelled_count += 1

    # # Just test data here
    # earnings_by_category["Business Dumpster"] = {"amount": 2000, "percent": 0}
    # earnings_by_category["Junk Removal"] = {"amount": 5000, "percent": 0}
    # earnings_by_category["Scissor Lift"] = {"amount": 100, "percent": 0}
    # earnings_by_category["Concrete & Masonary"] = {
    #     "amount": 50,
    #     "percent": 0,
    # }
    # earnings_by_category["Office Unit"] = {"amount": 25, "percent": 0}
    # earnings_by_category["Forklift"] = {"amount": 80, "percent": 0}
    # earnings_by_category["Boom Lifts"] = {"amount": 800, "percent": 0}
    # context["earnings"] += 200 + 500 + 100 + 50 + 25 + 80 + 800

    # Sort the dictionary by the 'amount' field in descending order
    sorted_categories = sorted(
        earnings_by_category.items(), key=lambda x: x[1]["amount"], reverse=True
    )

    # Calculate the 'percent' field for each category
    for category, data in sorted_categories:
        if context["earnings"] == 0:
            data["percent"] = int((data["amount"] / 1) * 100)
        else:
            data["percent"] = int((data["amount"] / context["earnings"]) * 100)

    # Create a new category 'Other' for the categories that are not in the top 4
    other_amount = sum(data["amount"] for category, data in sorted_categories[4:])
    if context["earnings"] == 0:
        other_percent = int((other_amount / 1) * 100)
    else:
        other_percent = int((other_amount / context["earnings"]) * 100)

    # Create the final dictionary
    final_categories = dict(sorted_categories[:4])
    final_categories["Other"] = {"amount": other_amount, "percent": other_percent}
    context["earnings_by_category"] = final_categories
    # print(final_categories)
    context["pending_count"] = pending_count
    # context["pending_count"] = orders.count()
    context["location_count"] = UserAddress.objects.filter(
        user_id=context["user"].id
    ).count()
    context["user_count"] = User.objects.filter(
        user_group_id=context["user"].user_group_id
    ).count()

    context["chart_data"] = json.dumps(get_dashboard_chart_data(earnings_by_month))

    if request.headers.get("HX-Request"):
        context["page_title"] = "Dashboard"
        return render(request, "customer_dashboard/snippets/dashboard.html", context)
    else:
        return render(request, "customer_dashboard/index.html", context)


@login_required(login_url="/admin/login/")
def new_order(request):
    context = {}
    context["user"] = get_user(request)
    main_product_categories = MainProductCategory.objects.all().order_by("sort")
    context["main_product_categories"] = main_product_categories

    return render(
        request, "customer_dashboard/new_order/main_product_categories.html", context
    )


@login_required(login_url="/admin/login/")
def new_order_category_price(request, category_id):
    context = {}
    main_product_category = MainProductCategory.objects.get(id=category_id)
    context["price_from"] = main_product_category.price_from
    # Assume htmx request
    # if request.headers.get("HX-Request"):
    return render(
        request, "customer_dashboard/snippets/category_price_from.html", context
    )


@login_required(login_url="/admin/login/")
def new_order_2(request, category_id):
    context = {}
    context["user"] = get_user(request)
    main_product_category = MainProductCategory.objects.filter(id=category_id)
    main_product_category = main_product_category.prefetch_related("main_products")
    main_product_category = main_product_category.first()
    main_products = main_product_category.main_products.all().order_by("sort")
    context["main_product_category"] = main_product_category
    context["main_products"] = []
    for main_product in main_products:
        main_product_dict = {}
        main_product_dict["product"] = main_product
        main_product_dict["infos"] = main_product.mainproductinfo_set.all().order_by(
            "sort"
        )
        context["main_products"].append(main_product_dict)

    return render(request, "customer_dashboard/new_order/main_products.html", context)


@login_required(login_url="/admin/login/")
def new_order_3(request, product_id):
    context = {}
    context["user"] = get_user(request)
    main_product = MainProduct.objects.filter(id=product_id)
    main_product = main_product.select_related("main_product_category")
    main_product = main_product.first()
    context["main_product"] = main_product
    product_waste_types = MainProductWasteType.objects.filter(
        main_product_id=main_product.id
    )
    product_waste_types = product_waste_types.select_related("waste_type")
    context["product_waste_types"] = product_waste_types
    add_ons = AddOn.objects.filter(main_product_id=product_id)
    # Get addon choices for each add_on and display the choices under the add_on.
    context["product_add_ons"] = []
    for add_on in add_ons:
        context["product_add_ons"].append(
            {"add_on": add_on, "choices": add_on.addonchoice_set.all()}
        )
    user_addresses = UserAddress.objects.filter(user_id=context["user"].id)
    context["user_addresses"] = user_addresses
    context["service_freqencies"] = ServiceRecurringFrequency.objects.all()
    return render(
        request, "customer_dashboard/new_order/main_product_detail.html", context
    )


def get_pricing(
    product_id: uuid.UUID,
    user_address_id: uuid.UUID,
    waste_type_id: uuid.UUID,
    seller_location_id: uuid.UUID = None,
):
    price_mod = pricing.Price_Model(
        data={
            "seller_location": seller_location_id,
            "product": product_id,
            "user_address": user_address_id,
            "waste_type": waste_type_id,
        }
    )

    # Get SellerLocations that offer the product.
    seller_products = SellerProduct.objects.filter(product_id=product_id)
    seller_product_seller_locations = SellerProductSellerLocation.objects.filter(
        seller_product__in=seller_products, active=True
    )

    return price_mod.get_prices(seller_product_seller_locations)


@login_required(login_url="/admin/login/")
def new_order_4(request):
    context = {}
    context["user"] = get_user(request)
    product_id = request.GET.get("product_id")
    user_address = request.GET.get("user_address")
    product_add_on_choices = []
    for key, value in request.GET.items():
        if key.startswith("product_add_on_choices"):
            product_add_on_choices.append(value)
    product_waste_types = request.GET.getlist("product_waste_types")
    service_frequency = request.GET.get("service_frequency")
    delivery_date = request.GET.get("delivery_date")
    removal_date = request.GET.get("removal_date")
    context["product_id"] = product_id
    context["user_address"] = user_address
    context["product_waste_types"] = product_waste_types
    context["product_add_on_choices"] = product_add_on_choices
    context["service_frequency"] = service_frequency
    context["delivery_date"] = delivery_date
    context["removal_date"] = removal_date
    # if product_waste_types:
    main_product_waste_type = MainProductWasteType.objects.filter(
        id=product_waste_types[0]
    ).first()

    products = Product.objects.filter(main_product_id=product_id)
    # Find the products that have the waste types and add ons.
    if product_add_on_choices:
        for product in products:
            product_addon_choices_db = ProductAddOnChoice.objects.filter(
                product_id=product.id
            ).values_list("add_on_choice_id", flat=True)
            if set(product_addon_choices_db) == set(product_add_on_choices):
                context["product"] = product
                break
    elif products.count() == 1:
        context["product"] = products.first()
    if context.get("product", None) is None:
        messages.error(request, "Product not found.")
        return HttpResponseRedirect(reverse("customer_new_order"))

    # We know the product the user wants
    seller_product_locations = SellerProductSellerLocation.objects.filter(
        seller_product__product_id=context["product"].id
    )

    # if request.method == "POST":
    context["seller_product_locations"] = []
    for seller_product_location in seller_product_locations:
        if hasattr(seller_product_location, "seller_location"):
            seller_d = {}
            seller_d["seller_product_location"] = seller_product_location
            pricing_data = get_pricing(
                context["product"].id,
                user_address,
                main_product_waste_type.waste_type_id,
                seller_location_id=seller_product_location.seller_location_id,
            )
            seller_d["price"] = float(pricing_data["service"]["rate"])
            context["seller_product_locations"].append(seller_d)
            break

    # context["seller_locations"] = seller_product_location.first().seller_location
    return render(
        request,
        "customer_dashboard/new_order/main_product_detail_pricing.html",
        context,
    )


@login_required(login_url="/admin/login/")
def new_order_5(request):
    context = {}
    context["user"] = get_user(request)
    context["cart"] = {}
    if request.method == "POST":
        # Create the order group and orders.
        seller_product_location_id = request.POST.get("seller_product_location_id")
        product_id = request.POST.get("product_id")
        user_address_id = request.POST.get("user_address")
        product_waste_types = request.POST.get("product_waste_types")
        if product_waste_types:
            product_waste_types = ast.literal_eval(product_waste_types)
        placement_details = request.POST.get("placement_details")
        # product_add_on_choices = request.POST.get("product_add_on_choices")
        service_frequency = request.POST.get("service_frequency")
        delivery_date = request.POST.get("delivery_date")
        removal_date = request.POST.get("removal_date")
        main_product = MainProduct.objects.filter(id=product_id)
        main_product = main_product.select_related("main_product_category")
        # main_product = main_product.prefetch_related("products")
        main_product = main_product.first()
        context["main_product"] = main_product
        seller_product_location = SellerProductSellerLocation.objects.get(
            id=seller_product_location_id
        )
        user_address = UserAddress.objects.filter(id=user_address_id).first()
        # create order group and orders
        # TODO: where do I get tonnage_quantity?
        order_group = OrderGroup(
            user=context["user"],
            user_address=user_address,
            seller_product_seller_location_id=seller_product_location_id,
            start_date=delivery_date,
            take_rate=30.0,
        )
        if service_frequency:
            order_group.service_recurring_frequency_id = service_frequency
        if removal_date:
            order_group.end_date = removal_date
        if seller_product_location.delivery_fee:
            order_group.delivery_fee = seller_product_location.delivery_fee
        if seller_product_location.removal_fee:
            order_group.removal_fee = seller_product_location.removal_fee
        order_group.save()
        # Create the order (Let submitted on null, this indicates that the order is in the cart)
        # The first order of an order group always gets the same start and end date.
        # if not removal_date:
        #     removal_date = delivery_date
        order = Order(
            order_group=order_group, start_date=delivery_date, end_date=delivery_date
        )
        order.save()
        # context["cart"][order_group.id] = {
        #     "order_group": order_group,
        #     "price": order.customer_price()
        # }
    elif request.method == "DELETE":
        # Delete the order group and orders.
        order_group_id = request.GET.get("id")
        subtotal = request.GET.get("subtotal")
        cart_count = request.GET.get("count")
        customer_price = request.GET.get("price")
        order_group = OrderGroup.objects.filter(id=order_group_id).first()
        if customer_price:
            customer_price = float(customer_price)
        else:
            customer_price = 0
        if order_group:
            # Delete any related protected objects, like orders and subscriptions.
            sub_obj = Subscription.objects.filter(order_group_id=order_group.id).first()
            if sub_obj:
                sub_obj.delete()
            for order in order_group.orders.all():
                # del_subtotal += order.customer_price()
                order.delete()
            order_group.delete()
        if subtotal:
            context["subtotal"] = float(subtotal) - float(customer_price)
        if cart_count:
            context["cart_count"] = int(cart_count) - 1
        if order_group:
            messages.success(request, "Order removed from cart.")
        else:
            messages.error(request, f"Order not found [{order_group_id}].")
        if request.headers.get("HX-Request"):
            return render(
                request,
                "customer_dashboard/new_order/cart_remove_item.html",
                context,
            )

    # Load the cart page
    context["subtotal"] = 0
    context["cart_count"] = 0
    # Pull all orders with submitted_on = None and show them in the cart.
    orders = (
        Order.objects.filter(order_group__user_id=context["user"].id)
        .filter(submitted_on__isnull=True)
        .order_by("-order_group__start_date")
    )
    if not orders:
        messages.error(request, "Your cart is empty.")
    else:
        # Get unique order group objects from the orders
        for order in orders:
            try:
                customer_price = order.customer_price()
                context["cart"][order.order_group.id]["price"] += customer_price
                context["cart"][order.order_group.id]["count"] += 1
                context["cart"][order.order_group.id]["status"] = order.status
                context["subtotal"] += customer_price
            except KeyError:
                customer_price = order.customer_price()
                context["cart"][order.order_group.id] = {
                    "order_group": order.order_group,
                    "price": customer_price,
                    "count": 1,
                    "status": order.status,
                }
                context["subtotal"] += customer_price
                context["cart_count"] += 1

    return render(
        request,
        "customer_dashboard/new_order/cart.html",
        context,
    )


@login_required(login_url="/admin/login/")
def new_order_6(request, order_group_id):
    context = {}
    context["user"] = get_user(request)
    count, deleted_objs = OrderGroup.objects.filter(id=order_group_id).delete()
    if count:
        messages.success(request, "Order removed from cart.")
    else:
        messages.error(request, f"Order not found [{order_group_id}].")
    return HttpResponseRedirect(reverse("customer_new_order"))


@login_required(login_url="/admin/login/")
def profile(request):
    context = {}
    user = get_user(request)
    context["user"] = user

    if request.method == "POST":
        # NOTE: Since email is disabled, it is never POSTed,
        # so we need to copy the POST data and add the email back in. This ensures its presence in the form.
        POST_COPY = request.POST.copy()
        POST_COPY["email"] = user.email
        form = UserForm(POST_COPY, request.FILES)
        context["form"] = form
        if form.is_valid():
            save_db = False
            if form.cleaned_data.get("first_name") != user.first_name:
                user.first_name = form.cleaned_data.get("first_name")
                save_db = True
            if form.cleaned_data.get("last_name") != user.last_name:
                user.last_name = form.cleaned_data.get("last_name")
                save_db = True
            if form.cleaned_data.get("phone") != user.phone:
                user.phone = form.cleaned_data.get("phone")
                save_db = True
            if form.cleaned_data.get("type") != user.type:
                user.type = form.cleaned_data.get("type")
                save_db = True
            if request.FILES.get("photo"):
                user.photo = request.FILES["photo"]
                save_db = True
            elif request.POST.get("photo-clear") == "on":
                user.photo = None
                save_db = True
            if save_db:
                context["user"] = user
                user.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            # Reload the form with the updated data (for some reason it doesn't update the form with the POST data).
            form = UserForm(
                initial={
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": user.phone,
                    "photo": user.photo,
                    "email": user.email,
                    "type": user.type,
                }
            )
            context["form"] = form
            # return HttpResponse("", status=200)
            # This is an HTMX request, so respond with html snippet
            # if request.headers.get("HX-Request"):
            return render(request, "customer_dashboard/profile.html", context)
        else:
            # This will let bootstrap know to highlight the fields with errors.
            for field in form.errors:
                form[field].field.widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
    else:
        form = UserForm(
            initial={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "photo": user.photo,
                "email": user.email,
                "type": user.type,
            }
        )
        context["form"] = form
    return render(request, "customer_dashboard/profile.html", context)


@login_required(login_url="/admin/login/")
def my_order_groups(request):
    context = {}
    context["user"] = get_user(request)
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    date = request.GET.get("date", None)
    location_id = request.GET.get("location_id", None)
    user_id = request.GET.get("user_id", None)
    try:
        is_active = int(request.GET.get("active", 1))
    except ValueError:
        is_active = 1
    query_params = request.GET.copy()
    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        if user_id:
            order_groups = OrderGroup.objects.filter(user_id=user_id)
        else:
            order_groups = OrderGroup.objects.filter(user_id=context["user"].id)

        if date:
            order_groups = order_groups.filter(end_date=date)
        if location_id:
            # TODO: Ask if location is user_address_id or seller_product_seller_location__seller_location_id
            order_groups = order_groups.filter(user_address_id=location_id)
        # Select related fields to reduce db queries.
        order_groups = order_groups.select_related(
            "seller_product_seller_location__seller_product__seller",
            "seller_product_seller_location__seller_product__product__main_product",
            # "user_address",
        )
        # order_groups = order_groups.prefetch_related("orders")
        order_groups = order_groups.order_by("-end_date")

        # Active orders are those that have an end_date in the future or are null (recurring orders).
        today = datetime.date.today()
        order_groups_lst = []
        for order_group in order_groups:
            if order_group.end_date and order_group.end_date < today:
                if not is_active:
                    order_groups_lst.append(order_group)
            else:
                if is_active:
                    order_groups_lst.append(order_group)

        paginator = Paginator(order_groups_lst, pagination_limit)
        page_obj = paginator.get_page(page_number)
        context["page_obj"] = page_obj

        if page_number is None:
            page_number = 1
        else:
            page_number = int(page_number)

        query_params["p"] = 1
        context["page_start_link"] = (
            f"/customer/order_groups/?{query_params.urlencode()}"
        )
        query_params["p"] = page_number
        context["page_current_link"] = (
            f"/customer/order_groups/?{query_params.urlencode()}"
        )
        if page_obj.has_previous():
            query_params["p"] = page_obj.previous_page_number()
            context["page_prev_link"] = (
                f"/customer/order_groups/?{query_params.urlencode()}"
            )
        if page_obj.has_next():
            query_params["p"] = page_obj.next_page_number()
            context["page_next_link"] = (
                f"/customer/order_groups/?{query_params.urlencode()}"
            )
        query_params["p"] = paginator.num_pages
        context["page_end_link"] = f"/customer/order_groups/?{query_params.urlencode()}"

        return render(
            request, "customer_dashboard/snippets/order_groups_table.html", context
        )
    else:
        if query_params.get("active") is None:
            query_params["active"] = 1
        context["active_orders_link"] = (
            f"/customer/order_groups/?{query_params.urlencode()}"
        )
        return render(request, "customer_dashboard/order_groups.html", context)


@login_required(login_url="/admin/login/")
def order_group_detail(request, order_group_id):
    context = {}
    context["user"] = get_user(request)
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    # order.order_group.user_address.access_details
    # order.order_group.placement_details
    order_group = OrderGroup.objects.filter(id=order_group_id)
    order_group = order_group.select_related(
        "seller_product_seller_location__seller_product__seller",
        "seller_product_seller_location__seller_product__product__main_product",
        "user_address",
    )
    order_group = order_group.prefetch_related("orders")
    order_group = order_group.first()
    context["order_group"] = order_group
    user_address = order_group.user_address
    context["user_address"] = user_address
    context["orders"] = order_group.orders.all()

    if request.method == "POST":
        try:
            save_model = None
            if "access_details_button" in request.POST:
                context["placement_form"] = PlacementDetailsForm(
                    initial={"placement_details": order_group.placement_details}
                )
                form = AccessDetailsForm(request.POST)
                context["access_form"] = form
                if form.is_valid():
                    if (
                        form.cleaned_data.get("access_details")
                        != user_address.access_details
                    ):
                        user_address.access_details = form.cleaned_data.get(
                            "access_details"
                        )
                        save_model = user_address
                else:
                    raise InvalidFormError(form, "Invalid AccessDetailsForm")
            elif "placement_details_button" in request.POST:
                context["access_form"] = AccessDetailsForm(
                    initial={"access_details": user_address.access_details}
                )
                form = PlacementDetailsForm(request.POST)
                context["placement_form"] = form
                if form.is_valid():
                    if (
                        form.cleaned_data.get("placement_details")
                        != order_group.placement_details
                    ):
                        order_group.placement_details = form.cleaned_data.get(
                            "placement_details"
                        )
                        save_model = order_group
                else:
                    raise InvalidFormError(form, "Invalid PlacementDetailsForm")
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            return render(
                request, "customer_dashboard/order_group_detail.html", context
            )
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                e.form[field].field.widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
            # messages.error(request, e.msg)
    else:
        context["access_form"] = AccessDetailsForm(
            initial={"access_details": user_address.access_details}
        )
        context["placement_form"] = PlacementDetailsForm(
            initial={"placement_details": order_group.placement_details}
        )

    return render(request, "customer_dashboard/order_group_detail.html", context)


@login_required(login_url="/admin/login/")
def order_detail(request, order_id):
    context = {}
    context["user"] = get_user(request)
    order = Order.objects.filter(id=order_id)
    order = order.select_related(
        "order_group__seller_product_seller_location__seller_product__seller",
        "order_group__user_address",
        "order_group__user",
        "order_group__seller_product_seller_location__seller_product__product__main_product",
    )
    order = order.prefetch_related("payouts", "order_line_items")
    context["order"] = order.first()

    return render(request, "customer_dashboard/order_detail.html", context)


@login_required(login_url="/admin/login/")
def locations(request):
    context = {}
    context["user"] = get_user(request)
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    query_params = request.GET.copy()
    user_addresses = UserAddress.objects.filter(user_id=context["user"].id)

    paginator = Paginator(user_addresses, pagination_limit)
    page_obj = paginator.get_page(page_number)
    context["page_obj"] = page_obj

    if page_number is None:
        page_number = 1
    else:
        page_number = int(page_number)

    query_params["p"] = 1
    context["page_start_link"] = f"/customer/locations/?{query_params.urlencode()}"
    query_params["p"] = page_number
    context["page_current_link"] = f"/customer/locations/?{query_params.urlencode()}"
    if page_obj.has_previous():
        query_params["p"] = page_obj.previous_page_number()
        context["page_prev_link"] = f"/customer/locations/?{query_params.urlencode()}"
    if page_obj.has_next():
        query_params["p"] = page_obj.next_page_number()
        context["page_next_link"] = f"/customer/locations/?{query_params.urlencode()}"
    query_params["p"] = paginator.num_pages
    context["page_end_link"] = f"/customer/locations/?{query_params.urlencode()}"
    return render(request, "customer_dashboard/locations.html", context)


@login_required(login_url="/admin/login/")
def location_detail(request, location_id):
    context = {}
    context["user"] = get_user(request)
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    user_address = UserAddress.objects.get(id=location_id)
    context["user_address"] = user_address
    if user_address.user_group_id:
        context["users"] = User.objects.filter(user_group_id=user_address.user_group_id)
        today = datetime.date.today()
        order_groups = OrderGroup.objects.filter(user_address_id=user_address.id)
        order_groups = order_groups.select_related(
            "seller_product_seller_location__seller_product__seller",
            "seller_product_seller_location__seller_product__product__main_product",
            # "user_address",
        )
        # order_groups = order_groups.prefetch_related("orders")
        order_groups = order_groups.order_by("-end_date")
        # Active orders are those that have an end_date in the future or are null (recurring orders).
        context["active_orders"] = []
        context["past_orders"] = []
        for order_group in order_groups:
            if order_group.end_date and order_group.end_date < today:
                if len(context["past_orders"]) < 2:
                    context["past_orders"].append(order_group)
            else:
                if len(context["active_orders"]) < 2:
                    context["active_orders"].append(order_group)
            # Only show the first 2 active and past order_groups.
            if len(context["active_orders"]) >= 2 and len(context["past_orders"]) >= 2:
                break
        # TODO: Maybe store these orders for this user in local cache so that, if see all is tapped, it will be faster.

    if request.method == "POST":
        try:
            save_model = None
            if "access_details_submit" in request.POST:
                form = AccessDetailsForm(request.POST)
                context["form"] = form
                if form.is_valid():
                    if (
                        form.cleaned_data.get("access_details")
                        != user_address.access_details
                    ):
                        user_address.access_details = form.cleaned_data.get(
                            "access_details"
                        )
                        save_model = user_address
                else:
                    raise InvalidFormError(form, "Invalid AccessDetailsForm")
            elif "user_address_submit" in request.POST:
                form = UserAddressForm(request.POST)
                context["user_address_form"] = form
                if form.is_valid():
                    if form.cleaned_data.get("name") != user_address.name:
                        user_address.name = form.cleaned_data.get("name")
                        save_model = user_address
                    if form.cleaned_data.get("address_type") != str(
                        user_address.user_address_type_id
                    ):
                        user_address.user_address_type_id = form.cleaned_data.get(
                            "address_type"
                        )
                        save_model = user_address
                    if form.cleaned_data.get("street") != user_address.street:
                        user_address.street = form.cleaned_data.get("street")
                        save_model = user_address
                    if form.cleaned_data.get("city") != user_address.city:
                        user_address.city = form.cleaned_data.get("city")
                        save_model = user_address
                    if form.cleaned_data.get("state") != user_address.state:
                        user_address.state = form.cleaned_data.get("state")
                        save_model = user_address
                    if form.cleaned_data.get("postal_code") != user_address.postal_code:
                        user_address.postal_code = form.cleaned_data.get("postal_code")
                        save_model = user_address
                    if form.cleaned_data.get("autopay") != user_address.autopay:
                        user_address.autopay = form.cleaned_data.get("autopay")
                        save_model = user_address
                    if form.cleaned_data.get("is_archived") != user_address.is_archived:
                        user_address.is_archived = form.cleaned_data.get("is_archived")
                        save_model = user_address
                    if (
                        form.cleaned_data.get("access_details")
                        != user_address.access_details
                    ):
                        user_address.access_details = form.cleaned_data.get(
                            "access_details"
                        )
                        save_model = user_address
                    if (
                        form.cleaned_data.get("allow_saturday_delivery")
                        != user_address.allow_saturday_delivery
                    ):
                        user_address.allow_saturday_delivery = form.cleaned_data.get(
                            "allow_saturday_delivery"
                        )
                        save_model = user_address
                    if (
                        form.cleaned_data.get("allow_sunday_delivery")
                        != user_address.allow_sunday_delivery
                    ):
                        user_address.allow_sunday_delivery = form.cleaned_data.get(
                            "allow_sunday_delivery"
                        )
                        save_model = user_address
                else:
                    raise InvalidFormError(form, "Invalid UserAddressForm")
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            return render(request, "customer_dashboard/location_detail.html", context)
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                e.form[field].field.widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
            # messages.error(request, e.msg)
    else:
        context["form"] = AccessDetailsForm(
            initial={"access_details": user_address.access_details}
        )
        context["user_address_form"] = UserAddressForm(
            initial={
                "name": user_address.name,
                "address_type": user_address.user_address_type_id,
                "street": user_address.street,
                "city": user_address.city,
                "state": user_address.state,
                "postal_code": user_address.postal_code,
                "is_archived": user_address.is_archived,
                "allow_saturday_delivery": user_address.allow_saturday_delivery,
                "allow_sunday_delivery": user_address.allow_sunday_delivery,
                "access_details": user_address.access_details,
            }
        )

    return render(request, "customer_dashboard/location_detail.html", context)


@login_required(login_url="/admin/login/")
def new_location(request):
    context = {}
    context["user"] = get_user(request)
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):

    if request.method == "POST":
        try:
            save_model = None
            if "user_address_submit" in request.POST:
                form = UserAddressForm(request.POST)
                context["user_address_form"] = form
                if form.is_valid():
                    name = form.cleaned_data.get("name")
                    address_type = form.cleaned_data.get("address_type")
                    street = form.cleaned_data.get("street")
                    city = form.cleaned_data.get("city")
                    state = form.cleaned_data.get("state")
                    postal_code = form.cleaned_data.get("postal_code")
                    autopay = form.cleaned_data.get("autopay")
                    is_archived = form.cleaned_data.get("is_archived")
                    access_details = form.cleaned_data.get("access_details")
                    allow_saturday_delivery = form.cleaned_data.get(
                        "allow_saturday_delivery"
                    )
                    allow_sunday_delivery = form.cleaned_data.get(
                        "allow_sunday_delivery"
                    )
                    user_address = UserAddress(
                        user_group_id=context["user"].user_group_id,
                        user_id=context["user"].id,
                        name=name,
                        street=street,
                        city=city,
                        state=state,
                        postal_code=postal_code,
                        autopay=autopay,
                        is_archived=is_archived,
                        allow_saturday_delivery=allow_saturday_delivery,
                        allow_sunday_delivery=allow_sunday_delivery,
                    )
                    if address_type:
                        user_address.user_address_type_id = address_type
                    if access_details:
                        user_address.access_details = access_details
                    save_model = user_address
                else:
                    raise InvalidFormError(form, "Invalid UserAddressForm")
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            return HttpResponseRedirect(reverse("customer_locations"))
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                e.form[field].field.widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
            # messages.error(request, e.msg)
    else:
        context["user_address_form"] = UserAddressForm()

    return render(request, "customer_dashboard/location_new_edit.html", context)


@login_required(login_url="/admin/login/")
def users(request):
    context = {}
    context["user"] = get_user(request)
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    user_id = request.GET.get("user_id", None)
    date = request.GET.get("date", None)
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    query_params = request.GET.copy()
    users = User.objects.filter(user_group_id=context["user"].user_group_id)
    if date:
        users = users.filter(date_joined__date=date)
    users = users.order_by("-date_joined")

    user_lst = []
    for user in users:
        user_dict = {}
        user_dict["user"] = user
        user_dict["meta"] = {
            "associated_locations": UserAddress.objects.filter(user_id=user.id).count()
        }
        user_lst.append(user_dict)

    paginator = Paginator(user_lst, pagination_limit)
    page_obj = paginator.get_page(page_number)
    context["page_obj"] = page_obj

    if page_number is None:
        page_number = 1
    else:
        page_number = int(page_number)

    query_params["p"] = 1
    context["page_start_link"] = f"/customer/users/?{query_params.urlencode()}"
    query_params["p"] = page_number
    context["page_current_link"] = f"/customer/users/?{query_params.urlencode()}"
    if page_obj.has_previous():
        query_params["p"] = page_obj.previous_page_number()
        context["page_prev_link"] = f"/customer/users/?{query_params.urlencode()}"
    if page_obj.has_next():
        query_params["p"] = page_obj.next_page_number()
        context["page_next_link"] = f"/customer/users/?{query_params.urlencode()}"
    query_params["p"] = paginator.num_pages
    context["page_end_link"] = f"/customer/users/?{query_params.urlencode()}"
    return render(request, "customer_dashboard/users.html", context)


@login_required(login_url="/admin/login/")
def user_detail(request, user_id):
    context = {}
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    user = User.objects.get(id=user_id)
    context["user"] = user
    if user.user_group_id:
        context["user_addresses"] = UserAddress.objects.filter(user_id=user.id)[0:3]
        order_groups = OrderGroup.objects.filter(user_id=user.id)
        # Select related fields to reduce db queries.
        order_groups = order_groups.select_related(
            "seller_product_seller_location__seller_product__seller",
            "seller_product_seller_location__seller_product__product__main_product",
            # "user_address",
        )
        # order_groups = order_groups.prefetch_related("orders")
        order_groups = order_groups.order_by("-end_date")

        today = datetime.date.today()
        context["active_orders"] = []
        context["past_orders"] = []
        for order_group in order_groups:
            if order_group.end_date and order_group.end_date < today:
                if len(context["past_orders"]) < 2:
                    context["past_orders"].append(order_group)
            else:
                if len(context["active_orders"]) < 2:
                    context["active_orders"].append(order_group)
            # Only show the first 2 active and past order_groups.
            if len(context["active_orders"]) >= 2 and len(context["past_orders"]) >= 2:
                break

    if request.method == "POST":
        # NOTE: Since email is disabled, it is never POSTed,
        # so we need to copy the POST data and add the email back in. This ensures its presence in the form.
        POST_COPY = request.POST.copy()
        POST_COPY["email"] = user.email
        form = UserForm(POST_COPY, request.FILES)
        context["form"] = form
        if form.is_valid():
            save_db = False
            if form.cleaned_data.get("first_name") != user.first_name:
                user.first_name = form.cleaned_data.get("first_name")
                save_db = True
            if form.cleaned_data.get("last_name") != user.last_name:
                user.last_name = form.cleaned_data.get("last_name")
                save_db = True
            if form.cleaned_data.get("phone") != user.phone:
                user.phone = form.cleaned_data.get("phone")
                save_db = True
            if form.cleaned_data.get("type") != user.type:
                user.type = form.cleaned_data.get("type")
                save_db = True
            if request.FILES.get("photo"):
                user.photo = request.FILES["photo"]
                save_db = True
            elif request.POST.get("photo-clear") == "on":
                user.photo = None
                save_db = True
            if save_db:
                context["user"] = user
                user.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            # Reload the form with the updated data (for some reason it doesn't update the form with the POST data).
            form = UserForm(
                initial={
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": user.phone,
                    "photo": user.photo,
                    "email": user.email,
                    "type": user.type,
                }
            )
            context["form"] = form
            # return HttpResponse("", status=200)
            # This is an HTMX request, so respond with html snippet
            # if request.headers.get("HX-Request"):
            return render(request, "customer_dashboard/user_detail.html", context)
        else:
            # This will let bootstrap know to highlight the fields with errors.
            for field in form.errors:
                form[field].field.widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
    else:
        form = UserForm(
            initial={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "photo": user.photo,
                "email": user.email,
                "type": user.type,
            }
        )
        context["form"] = form

    return render(request, "customer_dashboard/user_detail.html", context)


@login_required(login_url="/admin/login/")
def new_user(request):
    context = {}
    # TODO: Only allow admin to create new users.
    context["user"] = get_user(request)
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):

    if request.method == "POST":
        try:
            save_model = None
            POST_COPY = request.POST.copy()
            # POST_COPY["email"] = user.email
            form = UserForm(POST_COPY, request.FILES)
            context["form"] = form
            context["form"].fields["email"].disabled = False
            if form.is_valid():
                first_name = form.cleaned_data.get("first_name")
                last_name = form.cleaned_data.get("last_name")
                phone = form.cleaned_data.get("phone")
                email = form.cleaned_data.get("email")
                user_type = form.cleaned_data.get("type")
                user = User(
                    user_group_id=context["user"].user_group_id,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    type=user_type,
                )
                if phone:
                    user.phone = phone
                if request.FILES.get("photo"):
                    user.photo = request.FILES["photo"]
                save_model = user
            else:
                raise InvalidFormError(form, "Invalid UserForm")
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            return HttpResponseRedirect(reverse("customer_users"))
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                e.form[field].field.widget.attrs["class"] += " is-invalid"
    else:
        context["form"] = UserForm()
        context["form"].fields["email"].disabled = False

    return render(request, "customer_dashboard/user_new_edit.html", context)


@login_required(login_url="/admin/login/")
def invoices(request):
    context = {}
    context["user"] = get_user(request)
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    date = request.GET.get("date", None)
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    query_params = request.GET.copy()
    invoices = Invoice.objects.filter(user_address__user_id=context["user"].id)
    if date:
        invoices = invoices.filter(due_date__date=date)
    invoices = invoices.order_by("-due_date")
    today = datetime.date.today()
    context["total_paid"] = 0
    context["past_due"] = 0
    context["total_open"] = 0
    for invoice in invoices:
        context["total_paid"] += invoice.amount_paid
        context["total_open"] += invoice.amount_remaining
        if invoice.due_date.date() > today:
            context["past_due"] += invoice.amount_remaining

    paginator = Paginator(invoices, pagination_limit)
    page_obj = paginator.get_page(page_number)
    context["page_obj"] = page_obj

    if page_number is None:
        page_number = 1
    else:
        page_number = int(page_number)

    query_params["p"] = 1
    context["page_start_link"] = f"/customer/invoices/?{query_params.urlencode()}"
    query_params["p"] = page_number
    context["page_current_link"] = f"/customer/invoices/?{query_params.urlencode()}"
    if page_obj.has_previous():
        query_params["p"] = page_obj.previous_page_number()
        context["page_prev_link"] = f"/customer/invoices/?{query_params.urlencode()}"
    if page_obj.has_next():
        query_params["p"] = page_obj.next_page_number()
        context["page_next_link"] = f"/customer/invoices/?{query_params.urlencode()}"
    query_params["p"] = paginator.num_pages
    context["page_end_link"] = f"/customer/invoices/?{query_params.urlencode()}"
    return render(request, "customer_dashboard/invoices.html", context)
