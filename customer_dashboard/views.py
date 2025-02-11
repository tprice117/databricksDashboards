import ast
from collections import defaultdict
import datetime
import json
import logging
import time
import uuid
from decimal import Decimal
from functools import wraps
from typing import List, Union
from urllib.parse import urlencode
from itertools import groupby
from operator import attrgetter

import requests
import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import (
    F,
    OuterRef,
    Q,
    ExpressionWrapper,
    DurationField,
    Sum,
    Avg,
    Case,
    Value,
    When,
    IntegerField,
    Subquery,
    Count,
    Max,
)
from django.db.models.functions import Concat, Round, Coalesce
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.forms import inlineformset_factory
from common.forms import HiddenDeleteFormSet, MultiTabularFormSet

from admin_approvals.models import UserGroupAdminApprovalUserInvite
from api.models import (
    AddOn,
    FreightBundle,
    Industry,
    MainProduct,
    MainProductCategory,
    MainProductCategoryGroup,
    MainProductWasteType,
    Order,
    OrderLineItem,
    OrderGroup,
    OrderGroupAttachment,
    OrderReview,
    Product,
    ProductAddOnChoice,
    Seller,
    SellerLocation,
    SellerProductSellerLocation,
    Subscription,
    TimeSlot,
    User,
    UserAddress,
    UserGroup,
    UserGroupCreditApplication,
    UserGroupLegal,
)
from api.models.seller.seller_product_seller_location_material_waste_type import (
    SellerProductSellerLocationMaterialWasteType,
)
from api.models.user.user import CompanyUtils as UserUtils
from api.models.user.user_address import CompanyUtils as UserAddressUtils
from api.models.user.user_group import CompanyUtils as UserGroupUtils
from api.models.user.user_user_address import UserUserAddress
from api.models.waste_type import WasteType
from api.utils import auth0
from billing.models import Invoice
from cart.utils import CheckoutUtils, QuoteUtils, CartUtils, CardError
from common.models.choices.user_type import UserType
from common.utils.generate_code import get_otp
from common.utils.shade_hex import shade_hex_color
from common.utils import DistanceUtils
from communications.intercom.utils.utils import get_json_safe_value
from crm.models import Lead, UserSelectableLeadStatus, LeadNote
from matching_engine.matching_engine import MatchingEngine
from payment_methods.models import PaymentMethod
from pricing_engine.api.v1.serializers.response.pricing_engine_response import (
    PricingEngineResponseSerializer,
)
from pricing_engine.pricing_engine import PricingEngine

from .forms import (
    AccessDetailsForm,
    BrandingFormSet,
    CreditApplicationForm,
    NewLeadForm,
    LeadDetailForm,
    LeadNoteForm,
    BaseLeadNoteFormset,
    OrderGroupForm,
    OrderGroupSwapForm,
    OrderReviewFormSet,
    PlacementDetailsForm,
    OrderGroupAttachmentsForm,
    UserAddressForm,
    UserForm,
    UserGroupForm,
    paymentDetailsForm,
    EditOrderDateForm,
    UserGroupNewForm,
    UserInviteForm,
)

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


class InvalidFormError(Exception):
    """Exception raised for validation errors in the form."""

    def __init__(self, form, msg):
        self.form = form
        self.msg = msg

    def __str__(self):
        return self.msg


class UserAlreadyExistsError(Exception):
    """Exception raised if User already exists."""

    pass


class DecimalEncoder(json.JSONEncoder):
    """Encode Decimal objects to string."""

    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


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
    for i in range(11, 0, -1):
        months.append(all_months[(current_month - i) % 12])
        data.append(round(data_by_month[(current_month - i) % 12], 2))

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


def is_impersonating(request: HttpRequest) -> bool:
    return request.session.get("customer_user_id") and request.session.get(
        "customer_user_id"
    ) != str(request.user.id)


def get_user_group(request: HttpRequest) -> Union[UserGroup, None]:
    """Returns the current UserGroup. This handles the case where the user is impersonating another user.
    If the user is impersonating, it will return the UserGroup of the impersonated user.
    The the user is staff and is not impersonating a user, then it will return None.

    Args:
        request (HttpRequest): Current request object.

    Returns:
        [UserGroup, None]: Returns the UserGroup object or None. None means staff user.
    """

    if is_impersonating(request) and request.session["customer_user_group_id"]:
        user_group = UserGroup.objects.select_related("branding").get(
            id=request.session["customer_user_group_id"]
        )
    elif request.user.is_staff:
        user_group = None
    else:
        # Normal user
        if request.session.get("customer_user_group_id"):
            try:
                user_group = UserGroup.objects.select_related("branding").get(
                    id=request.session["customer_user_group_id"]
                )
            except UserGroup.DoesNotExist:
                logger.error(
                    f"get_user_group: UserGroup with id {request.session['customer_user_group_id']} not found for User {request.user.id}."
                )
                # Cache user_group id for faster lookups
                user_group = request.user.user_group
                if user_group:
                    request.session["customer_user_group_id"] = get_json_safe_value(
                        user_group.id
                    )
        else:
            # Cache user_group id for faster lookups
            user_group = request.user.user_group
            if user_group:
                request.session["customer_user_group_id"] = get_json_safe_value(
                    user_group.id
                )

    return user_group


def get_user(request: HttpRequest) -> User:
    """Returns the current user. This handles the case where the user is impersonating another user.

    Args:
        request (HttpRequest): Current request object.

    Returns:
        dict: Dictionary of the User object.
    """
    if is_impersonating(request):
        user = User.objects.get(id=request.session.get("customer_user_id"))
    else:
        user = request.user
    return user


def get_user_group_user_objects(
    request: HttpRequest, user: User, user_group: UserGroup, search_q: str = None
):
    """Returns the users for the current UserGroup.

    If user is:
        - staff, then all users are returned.
        - not staff
            - is admin, then return all users for the UserGroup.
            - not admin, then only users in the logged in user's user group.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        user_group (UserGroup): UserGroup object. NOTE: May be None.

    Returns:
        QuerySet[User]: The users queryset.
    """
    if not request.user.is_staff and user.type != UserType.ADMIN:
        users = User.objects.filter(user_group_id=user.user_group_id)
    else:
        if request.user.is_staff and not is_impersonating(request):
            # Global View: Get all users.
            users = User.objects.all()
        elif user_group:
            users = User.objects.filter(user_group_id=user_group.id)
        else:
            # Individual user.
            users = User.objects.filter(id=user.id)
    if search_q:
        users = users.filter(
            Q(first_name__icontains=search_q)
            | Q(last_name__icontains=search_q)
            | Q(email__icontains=search_q)
        )
    return users


def get_order_group_objects(request: HttpRequest, user: User, user_group: UserGroup):
    """Returns the order_groups for the current UserGroup.

    If user is:
        - staff, then all order_groups for all of UserGroups are returned.
        - not staff
            - is admin, then return all order_groups for the UserGroup.
            - not admin, then only order_groups for the UserGroup locations the user is associated with are returned.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        user_group (UserGroup): UserGroup object. NOTE: May be None.

    Returns:
        QuerySet[OrderGroup]: The order_groups queryset.
    """
    if not request.user.is_staff and user.type != UserType.ADMIN:
        user_user_location_ids = (
            UserUserAddress.objects.filter(user_id=user.id)
            .select_related("user_address")
            .values_list("user_address_id", flat=True)
        )
        order_groups = OrderGroup.objects.filter(
            user_address__in=user_user_location_ids
        )
    else:
        if request.user.is_staff and not is_impersonating(request):
            # Global View: Get all order_groups.
            order_groups = OrderGroup.objects.all()
        elif user_group:
            order_groups = OrderGroup.objects.filter(user__user_group_id=user_group.id)
        else:
            # Individual user. Get all orders for the user.
            order_groups = OrderGroup.objects.filter(user_id=user.id)
    return order_groups


def get_location_objects(
    request: HttpRequest,
    user: User,
    user_group: UserGroup,
    search_q: str = None,
    owner_id: str = None,
):
    """Returns the locations for the current UserGroup.

    If user is:
        - staff, then all locations for all of UserGroups are returned.
        - not staff
            - is admin, then return all locations for the UserGroup.
            - not admin, then only locations for the UserGroup locations the user is associated with are returned.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        user_group (UserGroup): UserGroup object. NOTE: May be None.
        search_q (str): [Optional] Search query string.
        owner_id (str): [Optional] ID of owner of usergroup. (Only if user is staff)

    Returns:
        QuerySet[UserAddress] : The locations queryset.
    """
    if not request.user.is_staff and user.type != UserType.ADMIN:
        locations = UserAddress.objects.for_user(user).order_by("-created_on")
    else:
        if request.user.is_staff and not is_impersonating(request):
            # Global View: Get all locations.
            locations = UserAddress.objects.for_user(request.user).order_by(
                "name", "-created_on"
            )
        elif user_group:
            locations = UserAddress.objects.filter(
                user_group_id=user_group.id
            ).order_by("-created_on")
        else:
            # Individual user. Get all locations for the user.
            locations = UserAddress.objects.for_user(user).order_by("-created_on")

    if search_q:
        locations = locations.filter(
            Q(name__icontains=search_q)
            | Q(street__icontains=search_q)
            | Q(city__icontains=search_q)
            | Q(state__icontains=search_q)
            | Q(postal_code__icontains=search_q)
        )
    if owner_id:
        locations = locations.filter(user_group__account_owner_id=owner_id)
    return locations


def get_invoice_objects(request: HttpRequest, user: User, user_group: UserGroup):
    """Returns the invoices for the current user_group.

    If user is:
        - staff, then all invoices for all of user_groups are returned.
        - not staff
            - is admin, then return all invoices for the user_group.
            - not admin, then only invoices for the user_group locations the user is associated with are returned.

    Args:
        request (HttpRequest): Request object from the view.
        user (User): User object.
        user_group (UserGroup): UserGroup object. NOTE: May be None.

    Returns:
        QuerySet[Invoice]: The invoices queryset.
    """

    if not request.user.is_staff and user.type != UserType.ADMIN:
        user_user_location_ids = (
            UserUserAddress.objects.filter(user_id=user.id)
            .select_related("user_address")
            .values_list("user_address_id", flat=True)
        )
        invoices = Invoice.objects.filter(user_address__in=user_user_location_ids)
    else:
        if request.user.is_staff and not is_impersonating(request):
            # Global View: Get all invoices.
            invoices = Invoice.objects.all()
        elif user_group:
            invoices = Invoice.objects.filter(user_address__user_group_id=user_group.id)
        else:
            # Individual user. Get all invoices for the user.
            invoices = Invoice.objects.filter(user_address__user_id=user.id)
    return invoices


########################
# Page views
########################
def catch_errors(redirect_url_name=None):
    """
    Decorator for views that enclose the view in a try/except block.
    If the test_func raises an exception, the decorator will catch it and
    attach a messages.error to the request object.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapper_view(request, *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
            except Exception as e:
                error_message = f"An unhandled error [{e}] occurred while accessing view [{str(view_func.__name__)}] on path [{request.get_full_path()}]"
                logger.error(
                    f"catch_errors: view: {str(view_func.__name__)} path:{request.get_full_path()}",
                    exc_info=e,
                )
                if request.headers.get("HX-Request"):
                    # Reraise htmx errors since those don't cause a 500 error.
                    raise
                # Add a _is_redirect flag to the redirect url to avoid infinite loops.
                query_params = request.GET.copy()
                _is_redirect = query_params.get("_is_redirect", None)
                if _is_redirect == "1" or _is_redirect == 1:
                    return render(
                        request,
                        "customer_dashboard/error.html",
                        {"error_message": error_message},
                    )
                messages.error(request, f"A server error occurred: {e}")
                query_params["_is_redirect"] = 1
                if redirect_url_name:
                    query_params.urlencode()
                    return HttpResponseRedirect(
                        f"{reverse(redirect_url_name)}?{query_params.urlencode()}"
                    )
                else:
                    full_path = f"{request.path}?{query_params.urlencode()}"
                    return HttpResponseRedirect(full_path)

        return _wrapper_view

    return decorator


def require_htmx(redirect_url_name=None):
    """
    Decorator for views that require an htmx request.
    If the request is not an htmx request, the decorator will redirect to the given url.
    If no url is given, it will return a 406 status code.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapper_view(request, *args, **kwargs):
            if not request.headers.get("HX-Request"):
                if redirect_url_name:
                    return HttpResponseRedirect(reverse(redirect_url_name))
                else:
                    return HttpResponse("Not Allowed", status=406)
            return view_func(request, *args, **kwargs)

        return _wrapper_view

    return decorator


# Add redirect to auth0 login if not logged in.
def customer_logout(request):
    logout(request)
    # Redirect to a success page.
    return HttpResponseRedirect("https://trydownstream.com/")


@login_required(login_url="/admin/login/")
def customer_search(request, is_selection=False):
    context = {}
    if request.method == "POST":
        search = request.POST.get("search")
        search = search.strip()
        if not search:
            return HttpResponse(status=204)
        try:
            search_id = uuid.UUID(search)
            user_groups = UserGroup.objects.filter(id=search_id)
            users = User.objects.filter(id=search_id)
        except ValueError:
            isearch = search.casefold()
            user_groups = UserGroup.objects.filter(name__icontains=isearch)
            users = User.objects.filter(
                Q(first_name__icontains=isearch)
                | Q(last_name__icontains=isearch)
                | Q(email__icontains=isearch)
                | Q(user_group__name__icontains=isearch)
            )
        context["user_groups"] = user_groups
        context["users"] = users

    if is_selection:
        return render(
            request,
            "customer_dashboard/snippets/user_group_search_selection.html",
            context,
        )
    else:
        return render(
            request, "customer_dashboard/snippets/user_search_list.html", context
        )


@login_required(login_url="/admin/login/")
def customer_impersonation_start(request):
    if request.user.is_staff:
        redirect_url = request.META.get("HTTP_REFERER", reverse("customer_home"))
        if request.method == "POST":
            user_group_id = request.POST.get("user_group_id")
            user_id = request.POST.get("user_id")
            if request.POST.get("redirect_url"):
                redirect_url = request.POST.get("redirect_url")
        elif request.method == "GET":
            user_group_id = request.GET.get("user_group_id")
            user_id = request.GET.get("user_id")
            if request.GET.get("redirect_url"):
                redirect_url = request.GET.get("redirect_url")
        else:
            return HttpResponse("Not Implemented", status=406)
        try:
            user = None
            if user_group_id:
                user_group = UserGroup.objects.get(id=user_group_id)
                user = user_group.users.filter(type=UserType.ADMIN).first()
            elif user_id:
                user = User.objects.get(id=user_id)
                # If user is an Admin, then set the user_group to enable global view.
                # NOTE: If staff user, then always show admin view.
                if user.type == UserType.ADMIN or request.user.is_staff:
                    user_group = user.user_group
                    if user_group:
                        user_group_id = user_group.id
            if not user:
                user = user_group.users.first()
                if not user:
                    raise User.DoesNotExist
                messages.warning(
                    request,
                    "No admin user found for UserGroup. UserGroup should have at least one admin user.",
                )
            if not user:
                raise User.DoesNotExist
            request.session["customer_user_group_id"] = get_json_safe_value(
                user_group_id
            )
            request.session["customer_user_id"] = get_json_safe_value(user.id)
            return HttpResponseRedirect(redirect_url)
        except User.DoesNotExist:
            messages.error(
                request,
                "No admin user found for UserGroup. UserGroup must have at least one admin user.",
            )
            return HttpResponseRedirect(redirect_url)
        except Exception:
            return HttpResponse("Not Found", status=404)
    else:
        return HttpResponse("Unauthorized", status=401)


@login_required(login_url="/admin/login/")
def customer_impersonation_stop(request):
    if request.session.get("customer_user_id"):
        del request.session["customer_user_id"]
    if request.session.get("customer_user_group_id"):
        del request.session["customer_user_group_id"]
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/customer/"))


def get_user_context(request: HttpRequest, add_user_group=True):
    """Returns the common context data for the views."""
    context = {}
    context["BASIS_THEORY_API_KEY"] = settings.BASIS_THEORY_PUB_API_KEY
    context["user"] = get_user(request)
    context["is_impersonating"] = is_impersonating(request)
    if request.user.is_authenticated and add_user_group:
        user_group = get_user_group(request)
        context["user_group"] = user_group
        context["theme"] = get_theme(user_group)
    return context


def get_theme(user_group: UserGroup):
    """Returns the theme colors for the given user group, or the default theme"""
    if user_group and hasattr(user_group, "branding"):
        return {
            "primary": user_group.branding.primary,
            "primary_hover": shade_hex_color(user_group.branding.primary, -0.15),
            "primary_active": shade_hex_color(user_group.branding.primary, -0.1),
            "secondary": user_group.branding.secondary,
        }
    return {
        "primary": "#018381",
        "primary_hover": "#016F6E",
        "primary_active": "#016967",
        "secondary": "#044162",
    }


@login_required(login_url="/admin/login/")
@catch_errors()
def index(request):
    context = get_user_context(request)
    if request.headers.get("HX-Request"):
        orders = CartUtils.get_booking_objects(
            request, context["user"], context["user_group"], is_impersonating(request)
        )
        orders = orders.filter(submitted_on__isnull=False).select_related(
            "order_group__seller_product_seller_location__seller_product__seller",
            "order_group__user_address",
            "order_group__user",
            "order_group__seller_product_seller_location__seller_product__product__main_product",
        )
        orders = orders.prefetch_related("payouts", "order_line_items")
        # .filter(status=Order.Status.PENDING)
        context["earnings"] = 0
        earnings_by_category = {}
        pending_count = 0
        scheduled_count = 0
        complete_count = 0
        cancelled_count = 0
        earnings_by_month = [0] * 12
        one_year_ago = datetime.date.today() - datetime.timedelta(days=365)
        for order in orders:
            context["earnings"] += float(order.customer_price())
            if order.end_date >= one_year_ago:
                earnings_by_month[order.end_date.month - 1] += float(
                    order.customer_price()
                )

            category = order.order_group.seller_product_seller_location.seller_product.product.main_product.main_product_category.name
            if category not in earnings_by_category:
                earnings_by_category[category] = {"amount": 0, "percent": 0}
            earnings_by_category[category]["amount"] += float(order.customer_price())

            if order.status == Order.Status.PENDING:
                pending_count += 1
            elif order.status == Order.Status.SCHEDULED:
                scheduled_count += 1
            elif order.status == Order.Status.COMPLETE:
                complete_count += 1
            elif order.status == Order.Status.CANCELLED:
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
        locations = get_location_objects(
            request, context["user"], context["user_group"]
        )
        if isinstance(locations, list):
            context["location_count"] = len(locations)
        else:
            context["location_count"] = locations.count()
        location_users = get_user_group_user_objects(
            request, context["user"], context["user_group"]
        )
        context["user_count"] = location_users.count()
        context["chart_data"] = get_dashboard_chart_data(earnings_by_month)
        # context["chart_data"] = json.dumps(get_dashboard_chart_data(earnings_by_month))

        return render(request, "customer_dashboard/snippets/dashboard.html", context)
    else:
        return render(request, "customer_dashboard/index.html", context)


# @login_required(login_url="/admin/login/")
@catch_errors()
def explore(request):
    context = get_user_context(request)

    search_q = request.GET.get("q", None)
    group_id = request.GET.get("group_id", None)
    categories_checked = request.GET.getlist("category", [])
    groups_checked = request.GET.getlist("category_group", [])
    industries_checked = request.GET.getlist("industry", [])
    allows_pick_up = request.GET.get("pickup", "False")

    main_products = (
        MainProduct.objects.all()
        .prefetch_related("images")
        .select_related("main_product_category", "main_product_category_group")
        .with_likes()
        .with_listings()
    )

    # Filter down query
    if search_q:
        main_products = main_products.filter(
            Q(name__icontains=search_q)
            | Q(main_product_category__name__icontains=search_q)
            | Q(main_product_category__group__name__icontains=search_q)
            | Q(main_product_category__industry__name__icontains=search_q)
        )
    if group_id:
        main_products = main_products.filter(main_product_category__group_id=group_id)
    if groups_checked:
        main_products = main_products.filter(
            main_product_category__group__slug__in=groups_checked
        )
    if categories_checked:
        main_products = main_products.filter(
            main_product_category__slug__in=categories_checked
        )
    if industries_checked:
        main_products = main_products.filter(
            main_product_category__industry__slug__in=industries_checked
        )
    if allows_pick_up == "True":
        main_products = main_products.filter(allows_pick_up=True)

    # Get main product categories with their listings so we can display categories with the most total listings first
    main_product_categories = list(
        MainProductCategory.objects.filter(main_products__in=main_products)
        .annotate(
            total_listings=Count(
                "main_products__products__seller_products__seller_product_seller_locations",
                distinct=True,
                filter=Q(main_products__in=main_products),
            )
        )
        .order_by("-total_listings")
        .values_list("id", flat=True)
    )

    # Paginate
    pagination_limit = 15
    page_number = 1
    if request.headers.get("HX-Request") and request.GET.get("p", None):
        # Only get the page number from query if it's an htmx request (load more button)
        page_number = request.GET.get("p")

    # Load page N
    paginator = Paginator(main_product_categories, pagination_limit)
    page_obj = paginator.get_page(page_number)

    # Filter down query to the page object
    main_products = main_products.filter(main_product_category__in=page_obj)

    # Create a dictionary to map category IDs to their order in page_obj
    category_order = {category_id: index for index, category_id in enumerate(page_obj)}

    carousels = [
        {
            "main_product_category": key,
            # Group is a generator, must evaluate to list here or else it will lose the data
            "main_products": list(group),
        }
        for key, group in groupby(
            main_products.order_by("main_product_category", "name"),
            key=attrgetter("main_product_category"),
        )
    ]

    # Sort the carousels by total listings
    context["carousels"] = sorted(
        carousels,
        key=lambda product: category_order[product["main_product_category"].id],
    )
    context["page_obj"] = page_obj

    if request.headers.get("HX-Request"):
        return render(
            request,
            "customer_dashboard/new_order/main_product_category_table.html",
            context,
        )

    # Checkboxes
    # Float checkboxes that have already been selected to appear at the top of the list
    # Reorder main product category groups
    if groups_checked:
        preserved_order = Case(
            # Generate list of position orders
            *[When(slug=slug, then=pos) for pos, slug in enumerate(groups_checked)],
            # default is end of groups list
            default=Value(len(groups_checked)),
            output_field=IntegerField(),
        )
        main_product_category_groups = MainProductCategoryGroup.objects.all().order_by(
            preserved_order, "name"
        )
    else:
        main_product_category_groups = MainProductCategoryGroup.objects.all().order_by(
            "name"
        )

    # Reorder categories
    if categories_checked:
        preserved_order = Case(
            *[When(slug=slug, then=pos) for pos, slug in enumerate(categories_checked)],
            default=Value(len(categories_checked)),
            output_field=IntegerField(),
        )
        categories = MainProductCategory.objects.all().order_by(preserved_order, "name")
    else:
        categories = MainProductCategory.objects.all().order_by("name")

    # Reorder industries
    if industries_checked:
        preserved_order = Case(
            *[When(slug=slug, then=pos) for pos, slug in enumerate(industries_checked)],
            default=Value(len(industries_checked)),
            output_field=IntegerField(),
        )
        industries = Industry.objects.all().order_by(preserved_order, "sort", "name")
    else:
        industries = Industry.objects.all().order_by("sort", "name")

    context.update(
        {
            "main_product_category_groups": main_product_category_groups,
            "categories": categories,
            "industries": industries,
        }
    )

    return render(
        request, "customer_dashboard/new_order/main_product_categories.html", context
    )


@login_required(login_url="/admin/login/")
def new_order_category_price(request, category_slug):
    context = {}
    # NOTE: Causes a lot of heavy db queries. Need to optimize.
    main_product_category = MainProductCategory.objects.get(slug=category_slug)
    context["price_from"] = main_product_category.price_from
    # Assume htmx request
    # if request.headers.get("HX-Request"):
    return render(
        request, "customer_dashboard/snippets/category_price_from.html", context
    )


@login_required(login_url="/admin/login/")
@require_GET
def user_address_search(request):
    search = request.GET.get("q")
    if not search:
        return HttpResponse(status=204)

    context = {}
    search = search.strip()
    user_addresses = UserAddress.objects.none()
    if user_id := request.GET.get("user"):
        if user_id != "None":
            user = User.objects.get(id=user_id)
            # Don't use request.user here, as we want to show the locations for the user only.
            user_addresses = (
                UserAddress.objects.for_user(user)
                .filter(
                    Q(name__icontains=search)
                    | Q(street__icontains=search)
                    | Q(city__icontains=search)
                    | Q(state__icontains=search)
                    | Q(postal_code__icontains=search)
                )
                .order_by("-created_on")
            )
    else:
        try:
            user_address_id = uuid.UUID(search)
            user_addresses = UserAddress.objects.filter(id=user_address_id)
        except ValueError:
            context.update(get_user_context(request))
            user_addresses = get_location_objects(
                request, context["user"], context["user_group"], search_q=search
            )

    context["user_addresses"] = user_addresses

    return render(
        request,
        "customer_dashboard/snippets/user_address_search_selection.html",
        context,
    )


# @login_required(login_url="/admin/login/")
@catch_errors()
def new_order_2(request, category_id):
    context = get_user_context(request)

    main_product_category = MainProductCategory.objects.filter(id=category_id)

    if not main_product_category.exists():
        messages.error(request, "Product not found.")
        return HttpResponseRedirect(reverse("customer_home"))

    main_product_category = main_product_category.prefetch_related(
        "main_products__mainproductinfo_set"
    ).first()

    main_products = main_product_category.main_products.all().order_by("sort")
    # if this is a search then filter the main products
    search_q = request.GET.get("q", None)
    if search_q:
        main_products = main_products.filter(name__icontains=search_q)
    context["main_product_category"] = main_product_category
    context["category_id"] = category_id
    context["main_products"] = []
    for main_product in main_products:
        main_product_dict = {}
        main_product_dict["product"] = main_product
        main_product_dict["infos"] = main_product.mainproductinfo_set.all().order_by(
            "sort"
        )
        context["main_products"].append(main_product_dict)

    if request.headers.get("HX-Request"):
        return render(
            request,
            "customer_dashboard/new_order/main_product_table.html",
            context,
        )

    return render(request, "customer_dashboard/new_order/main_products.html", context)


@catch_errors()
def product_details(request, product_slug):
    main_product = MainProduct.objects.filter(slug=product_slug)
    if not main_product.exists():
        messages.error(request, "Product not found.")
        return HttpResponseRedirect(reverse("customer_home"))
    return new_order_3(request, main_product)


@catch_errors()
def product_details_legacy(request, product_id):
    main_product = MainProduct.objects.filter(id=product_id)
    if not main_product.exists():
        messages.error(request, "Product not found.")
        return HttpResponseRedirect(reverse("customer_home"))
    return new_order_3(request, main_product)


@catch_errors()
def new_order_3(request, main_product):
    context = get_user_context(request)
    # TODO: Add a button that allows adding an address.
    # The button could open a modal that allows adding an address.
    main_product = main_product.select_related(
        "main_product_category"
    ).prefetch_related("images", "related_products")
    main_product = main_product.first()

    context["main_product"] = main_product
    context["product_id"] = main_product.id
    product_waste_types = MainProductWasteType.objects.filter(
        main_product_id=main_product.id
    )
    product_waste_types = product_waste_types.select_related("waste_type")
    context["product_waste_types"] = product_waste_types
    add_ons = AddOn.objects.filter(main_product_id=main_product.id)
    # Get addon choices for each add_on and display the choices under the add_on.
    # TODO: Should I only show ProductAddOnChoice so we know the product actually has these?
    context["product_add_ons"] = []
    for add_on in add_ons:
        context["product_add_ons"].append(
            {"add_on": add_on, "choices": add_on.choices.all()}
        )
    context["user_addresses"] = (
        get_location_objects(request, context["user"], context["user_group"])
        if request.user.is_authenticated
        else []
    )
    context["field_icons"] = {
        "product_waste_types": "fa-dumpster",
        "address": "fa-map-marker-alt",
        "shift_count": "fa-sync-alt",
        "schedule_window": "fa-clock",
        "delivery_date": "fa-calendar-check",
        "removal_date": "fa-calendar-times",
        "times_per_week": "fa-calendar-alt",
        "quantity": "fa-boxes",
    }
    if request.method == "POST":
        user_address_id = request.POST.get("user_address")
        if user_address_id:
            context["selected_user_address"] = UserAddress.objects.get(
                id=user_address_id
            )

        # Get the selected product add-ons
        selected_add_ons = []
        for key, value in request.POST.items():
            if key.startswith("product_add_on_choices_"):
                selected_add_ons.append(value)

        query_params = {
            "product_id": context["product_id"],
            "user_address": request.POST.get("user_address"),
            "delivery_date": request.POST.get("delivery_date"),
            "removal_date": request.POST.get("removal_date"),
            "schedule_window": request.POST.get("schedule_window"),
            "product_add_on_choices": selected_add_ons,
            "product_waste_types": request.POST.getlist("product_waste_types"),
            "related_products": request.POST.getlist("related_products"),
            "quantity": request.POST.get("quantity"),
        }
        if request.POST.get("times_per_week"):
            query_params["times_per_week"] = request.POST.get("times_per_week")
        if request.POST.get("shift_count"):
            query_params["shift_count"] = request.POST.get("shift_count")
        if not query_params["removal_date"]:
            # This happens for one-time orders like junk removal,
            # where the removal date is the same as the delivery date.
            query_params["removal_date"] = query_params["delivery_date"]
        try:
            form = OrderGroupForm(
                request.POST,
                request.FILES,
                user_addresses=context["user_addresses"],
                main_product=context["main_product"],
                product_waste_types=context["product_waste_types"],
                product_add_ons=context["product_add_ons"],
            )
            context["form"] = form
            # Use Django form validation to validate the form.
            # If not valid, then display error message.
            # If valid, then redirect to next page.
            if form.is_valid():
                pass
            else:
                raise InvalidFormError(form, "Invalid OrderGroupForm")
            return HttpResponseRedirect(
                f"{reverse('customer_new_order_4')}?{urlencode(query_params, doseq=True)}"
            )
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
        except Exception as e:
            messages.error(
                request, f"Error saving, please contact us if this continues: [{e}]."
            )
    else:
        context["form"] = OrderGroupForm(
            user_addresses=context["user_addresses"],
            main_product=context["main_product"],
            product_waste_types=context["product_waste_types"],
            product_add_ons=context["product_add_ons"],
        )

    return render(
        request, "customer_dashboard/new_order/main_product_detail.html", context
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def new_order_4(request):
    # Get context data
    context = get_user_context(request)
    try:
        context["product_id"] = request.GET.get("product_id")
        context["user_address"] = request.GET.get("user_address")
        context["product_waste_types"] = request.GET.getlist("product_waste_types")
        if context["product_waste_types"] and context["product_waste_types"][0] == "":
            context["product_waste_types"] = []
        context["product_add_on_choices"] = request.GET.getlist(
            "product_add_on_choices"
        )
        if (
            context["product_add_on_choices"]
            and context["product_add_on_choices"][0] == ""
        ):
            context["product_add_on_choices"] = []
        context["related_products"] = request.GET.getlist("related_products", [])
        context["schedule_window"] = request.GET.get("schedule_window", "")
        context["times_per_week"] = request.GET.get("times_per_week", "")
        if context["times_per_week"]:
            context["times_per_week"] = int(context["times_per_week"])
        context["shift_count"] = request.GET.get("shift_count", "")
        if context["shift_count"]:
            context["shift_count"] = int(context["shift_count"])
        context["delivery_date"] = request.GET.get("delivery_date")
        context["removal_date"] = request.GET.get("removal_date", "")
        context["quantity"] = int(request.GET.get("quantity"))
        context["project_id"] = request.GET.get("project_id")

        if context["delivery_date"]:
            context["delivery_date"] = datetime.datetime.strptime(
                context["delivery_date"], "%Y-%m-%d"
            ).date()
        if context["removal_date"]:
            context["removal_date"] = datetime.datetime.strptime(
                context["removal_date"], "%Y-%m-%d"
            ).date()

        # Get Product and AddOns
        products = Product.objects.filter(main_product_id=context["product_id"])

        if context["product_add_on_choices"]:
            prod_addon_choice_set = set(context["product_add_on_choices"])
            for product in products:
                product_addon_choices_db = ProductAddOnChoice.objects.filter(
                    product_id=product.id
                ).values_list("add_on_choice_id", flat=True)
                db_choices = set([str(choice) for choice in product_addon_choices_db])
                if db_choices == prod_addon_choice_set:
                    context["product"] = product
                    break
        elif products.count() == 1:
            context["product"] = products.first()
        elif products.count() > 1:
            messages.error(
                request,
                "Multiple products found. Only one product of each type should exist. You might encounter errors.",
            )
            context["product"] = products.first()
        if context.get("product", None) is None:
            messages.error(request, "Product not found.")
            return HttpResponseRedirect(reverse("customer_home"))

        # Discount
        context["max_discount_100"] = round(
            float(context["product"].main_product.max_discount) * 100, 1
        )
        discount = 0
        context["market_discount"] = (
            context["product"].main_product.max_discount * Decimal(0.8)
        ) * 100

        if not request.user.is_staff:
            discount = context["market_discount"]
        context["discount"] = discount
        context["default_markup"] = context["product"].main_product.default_take_rate
    except Exception as e:
        pass

    if request.headers.get("HX-Request"):
        # Waste type
        waste_type = None
        waste_type_id = None
        product = context["product"]
        # TODO: We are only using the first waste type for now.
        if context["product_waste_types"]:
            main_product_waste_type = MainProductWasteType.objects.filter(
                id=context["product_waste_types"][0]
            ).first()
            waste_type = main_product_waste_type.waste_type
            waste_type_id = waste_type.id
        if waste_type_id:
            context["waste_type"] = waste_type_id
            context["waste_type_name"] = waste_type.name

        # SellerProductSellerLocations
        user_address_obj = UserAddress.objects.filter(
            id=context["user_address"]
        ).first()
        seller_product_seller_locations = (
            MatchingEngine.get_possible_seller_product_seller_locations(
                product,
                user_address_obj,
                waste_type,
                related_products=context["related_products"],
            )
        )

        listing_buckets = defaultdict(
            lambda: {
                "location": None,
                "distance": None,
                "listing": {},
                "related": [],
                "related_ids": [],
                "total": 0.0,
                "delivery": 0.0,
                "removal": 0.0,
                "fuel_and_environmental": 0.0,
                "freight": 0.0,
            }
        )

        for seller_product_seller_location in seller_product_seller_locations:
            seller_d = {}
            try:
                # Include because SellerProductSellerLocationSerializer does not include waste types info needed for price_details_modal.
                seller_location = seller_product_seller_location.seller_location
                bucket = listing_buckets[seller_location.id]
                if not bucket["location"]:
                    bucket["location"] = seller_location
                    # show distance if they want to do a pickup
                    bucket["distance"] = DistanceUtils.get_driving_distance(
                        seller_location.latitude,
                        seller_location.longitude,
                        user_address_obj.latitude,
                        user_address_obj.longitude,
                    )

                seller_d["seller_product_seller_location"] = (
                    seller_product_seller_location
                )

                if seller_product_seller_location.seller_product.product.product_add_on_choices.exists():
                    seller_d["product_add_ons"] = [
                        choice.add_on_choice.name
                        for choice in seller_product_seller_location.seller_product.product.product_add_on_choices.all()
                    ]

                main_product = (
                    seller_product_seller_location.seller_product.product.main_product
                )

                pricing = PricingEngine.get_price(
                    user_address=UserAddress.objects.get(
                        id=context["user_address"],
                    ),
                    seller_product_seller_location=seller_product_seller_location,
                    start_date=context["delivery_date"],
                    end_date=context["removal_date"],
                    waste_type=(
                        WasteType.objects.get(id=waste_type_id)
                        if waste_type_id and main_product.has_material
                        else None
                    ),
                    times_per_week=(
                        context["times_per_week"]
                        if context["times_per_week"]
                        and main_product.has_service_times_per_week
                        else None
                    ),
                    shift_count=(
                        context["shift_count"]
                        if context["shift_count"] and main_product.has_rental_multi_step
                        else None
                    ),
                    discount=discount,
                )

                price_data = PricingEngineResponseSerializer(pricing).data
                # Breakdown of the price data because the neccessary calculations are not capable within the Django template.
                seller_d["price_breakdown"] = QuoteUtils.get_price_breakdown(
                    price_data,
                    seller_product_seller_location,
                    main_product,
                    user_group=context["user_group"],
                )

                # Check if the product should be treated as the main listing or a related listing.
                if (
                    main_product.id != product.main_product.id
                    and main_product.is_related
                ):
                    bucket["related"].append(seller_d)
                    bucket["related_ids"].append(seller_product_seller_location.id)
                else:
                    bucket["listing"] = seller_d

                # Update running totals
                if seller_d["price_breakdown"]["delivery"]:
                    bucket["delivery"] += seller_d["price_breakdown"]["delivery"][
                        "total"
                    ]
                if seller_d["price_breakdown"]["removal"]:
                    bucket["removal"] += seller_d["price_breakdown"]["removal"]["total"]
                bucket["fuel_and_environmental"] += seller_d["price_breakdown"][
                    "one_time"
                ]["fuel_and_environmental"]
                bucket["freight"] += seller_d["price_breakdown"]["one_time"]["total"]
                bucket["total"] += seller_d["price_breakdown"]["total"]
            except Exception as e:
                logger.error(
                    f"new_order_4:Error getting pricing [SellerProductSellerLocation: {seller_product_seller_location.id}]-[{e}]-[{request.build_absolute_uri()}]",
                    exc_info=e,
                )

        # Filter out results that don't have a listing or all the related products.
        # Maybe in the future we'll still want to show these off to the side somewhere.
        related_product_count = len(context["related_products"])
        context["seller_product_seller_locations"] = [
            obj
            for obj in listing_buckets.values()
            if obj["listing"] and len(obj["related_ids"]) == related_product_count
        ]

        try:
            # Sort the seller_product_seller_locations by total price (low to high).
            context["seller_product_seller_locations"].sort(
                key=lambda x: x["total"],
            )
        except Exception as e:
            logger.error(f"Error sorting seller_product_seller_locations: {e}")

        return render(
            request,
            "customer_dashboard/new_order/main_product_detail_pricing_list.html",
            context,
        )

    context["data_link"] = request.get_full_path()

    return render(
        request,
        "customer_dashboard/new_order/main_product_detail_pricing.html",
        context,
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def customer_cart_date_edit(request, order_id):
    if request.method == "POST":
        # a snippet of html for editing the start date
        context = get_user_context(request)
        order = (
            Order.objects.filter(id=order_id)
            .select_related(
                "order_group__seller_product_seller_location__seller_product__product__main_product"
            )
            .first()
        )
        customer_price = order.customer_price()
        customer_price_with_tax = order.customer_price_with_tax()
        context["cart_address"] = {"address": order.order_group.user_address}
        context["item"] = {
            "order": order,
            "main_product": order.order_group.seller_product_seller_location.seller_product.product.main_product,
            "subtotal": customer_price,
            "rpp": order.get_rpp_fee(),
            "tax": customer_price_with_tax - customer_price,
            "total": customer_price_with_tax,
        }
        context["loopcount"] = request.POST.get("loopcount")

        # the form was cancelled
        if request.POST.get("cancel"):
            return render(
                request,
                "customer_dashboard/new_order/cart_order_item.html",
                context,
            )
        if not request.POST.get("save"):
            if (
                order.order_type == Order.Type.DELIVERY
                or order.order_type == Order.Type.PICKUP
            ):
                form = EditOrderDateForm(
                    instance=order,
                    initial={"date": order.start_date.strftime("%Y-%m-%d")},
                )
            else:
                form = EditOrderDateForm(
                    instance=order,
                    initial={"date": order.end_date.strftime("%Y-%m-%d")},
                )

        def fullPageReload():
            # context["reload"] = True
            # use hx-refresh to reload the page
            response = render(
                request,
                "customer_dashboard/new_order/cart_order_item.html",
                context,
            )
            response["HX-Refresh"] = "true"
            return response

        if request.POST.get("save"):
            if (
                order.order_type == Order.Type.DELIVERY
                or order.order_type == Order.Type.PICKUP
            ):
                form = EditOrderDateForm(
                    request.POST,
                    request.FILES,
                    instance=order,
                    initial={"date": order.start_date.strftime("%Y-%m-%d")},
                )
            else:
                form = EditOrderDateForm(
                    request.POST,
                    request.FILES,
                    instance=order,
                    initial={"date": order.end_date.strftime("%Y-%m-%d")},
                )

            if form.is_valid():
                new_date = form.cleaned_data.get("date")
                try:
                    reschedule_result = order.reschedule_order(new_date)
                    if reschedule_result:
                        messages.success(request, "Successfully saved!")
                        return fullPageReload()
                    else:
                        messages.error(request, "Order start date not changed.")
                except ValidationError as e:
                    messages.error(
                        request,
                        f"Error rescheduling order: {e}",
                    )
                    return fullPageReload()
            else:
                messages.error(
                    request,
                    "Invalid date. Please check the form for errors.",
                )
                context["form"] = form
        else:
            context["form"] = form

        # form.save()
        # redirect to cart
        # return HttpResponseRedirect(reverse("customer_cart"))
        return render(
            request,
            "customer_dashboard/new_order/cart_order_item.html",
            context,
        )


@login_required(login_url="/admin/login/")
@catch_errors()
@require_http_methods(["GET", "POST"])
@require_htmx(redirect_url_name="customer_cart")
def customer_cart_po(request, order_group_id):
    """Returns a snippet with the project id for an order group. POST to update the project id."""
    context = {}
    order_group = OrderGroup.objects.get(id=order_group_id)
    user = get_user(request)

    # Authorize the request.
    if not (
        user.is_staff
        or (
            user.type == UserType.ADMIN
            and (
                order_group.user == user
                or user.user_group == order_group.user.user_group
            )
        )
        or order_group.user_address.user == user
    ):
        return HttpResponse("Unauthorized", status=401)

    if request.method == "POST":
        project_id = request.POST.get("project_id")

        order_group.project_id = project_id
        order_group.save()

    context["order_group"] = order_group

    return render(
        request, "customer_dashboard/snippets/cart_order_item_po.html", context
    )


@login_required(login_url="/admin/login/")
@catch_errors()
@require_GET
@require_htmx(redirect_url_name="customer_cart")
def customer_cart_po_edit(request, order_group_id):
    """Returns a snippet with a form to edit the project id of an order group."""
    context = {}
    order_group = OrderGroup.objects.get(id=order_group_id)
    user = get_user(request)

    # Authorize the request.
    if not (
        user.is_staff
        or (
            user.type == UserType.ADMIN
            and (
                order_group.user == user
                or user.user_group == order_group.user.user_group
            )
        )
        or order_group.user_address.user == user
    ):
        return HttpResponse("Unauthorized", status=401)

    context["order_group"] = order_group
    return render(
        request, "customer_dashboard/snippets/cart_order_item_po_edit.html", context
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def cart(request):
    context = get_user_context(request)
    context["cart"] = {}
    if request.method == "POST":
        # Create the order group and orders.
        seller_product_seller_location_id = request.POST.get(
            "seller_product_seller_location_id"
        )
        product_id = request.POST.get("product_id")
        user_address_id = request.POST.get("user_address")
        product_waste_types = request.POST.get("product_waste_types")
        if product_waste_types:
            product_waste_types = ast.literal_eval(product_waste_types)
        waste_type_id = request.POST.get("waste_type")
        schedule_window = request.POST.get("schedule_window", "Morning (7am-11am)")
        times_per_week = (
            int(request.POST.get("times_per_week"))
            if request.POST.get("times_per_week")
            else None
        )
        shift_count = (
            int(request.POST.get("shift_count"))
            if request.POST.get("shift_count")
            else None
        )
        delivery_date = datetime.datetime.strptime(
            request.POST.get("delivery_date"),
            "%Y-%m-%d",
        ).date()
        quantity = (
            int(request.POST.get("quantity")) if request.POST.get("quantity") else 1
        )
        project_id = request.POST.get("project_id")
        is_delivery = request.POST.get("is_delivery", "True").lower() == "true"
        related_products = request.POST.getlist("related_products", [])

        seller_product_locations = SellerProductSellerLocation.objects.filter(
            Q(id=seller_product_seller_location_id) | Q(id__in=related_products)
        ).select_related("seller_product__product__main_product__main_product_category")
        user_address = UserAddress.objects.get(id=user_address_id)

        with transaction.atomic():
            # It's not the most efficient to loop through the quantity and create the orders,
            # but eventually 'quantity' will be moved to the cart instead of the product details.
            # Cache the order_groups in local memory to clone them.
            order_groups = {}

            for i in range(quantity):
                parent_booking = None
                related_bookings = []

                for seller_product_location in seller_product_locations:
                    if not order_groups.get(seller_product_location.id):
                        main_product = (
                            seller_product_location.seller_product.product.main_product
                        )
                        # make sure you cannot select pickup if main product does not allow pickup
                        if not main_product.allows_pick_up:
                            is_delivery = True

                        # Discount
                        discount: Decimal = 0.0

                        if not request.user.is_staff:
                            # User is not staff, meaning discount is set to market discount.
                            discount = main_product.max_discount * Decimal(0.8) * 100
                        else:
                            # User is staff.
                            discount = Decimal(request.POST.get("discount", "0"))
                            max_discount_100 = round(main_product.max_discount * 100, 1)

                            if discount > max_discount_100:
                                # Discount is larger than max discount.
                                messages.error(
                                    request,
                                    "The selected discount exceeds the maximum allowed limit. Max discount applied.",
                                )
                                discount = max_discount_100

                        # Waste type
                        if main_product.has_material and hasattr(
                            seller_product_location, "material"
                        ):
                            material_waste_type = (
                                SellerProductSellerLocationMaterialWasteType.objects.filter(
                                    seller_product_seller_location_material=seller_product_location.material
                                )
                                .filter(
                                    main_product_waste_type__waste_type_id=waste_type_id
                                )
                                .first()
                            )
                            if not material_waste_type:
                                messages.error(
                                    request,
                                    "Material waste type not found. Please contact us if this continues.",
                                )
                                return HttpResponseRedirect(reverse("customer_home"))

                        # Get the default take rate and calculate the take rate based on the discount.
                        default_take_rate_percent: Decimal = (
                            main_product.default_take_rate / 100
                        )
                        default_price_multiplier = 1 + default_take_rate_percent
                        discount_percent = discount / 100
                        price_with_discount = default_price_multiplier * (
                            1 - discount_percent
                        )
                        take_rate = price_with_discount - 1

                        # Create order group and orders
                        order_group = OrderGroup(
                            user=context["user"],
                            user_address=user_address,
                            seller_product_seller_location_id=seller_product_location.id,
                            start_date=delivery_date,
                            take_rate=take_rate * 100,
                            is_delivery=is_delivery,
                        )
                        if times_per_week and main_product.has_service_times_per_week:
                            order_group.times_per_week = times_per_week
                        if shift_count and main_product.has_rental_multi_step:
                            order_group.shift_count = shift_count
                        if waste_type_id and main_product.has_material:
                            order_group.waste_type_id = waste_type_id

                        # NOTE: Commenting removal_date out for now. We may, possibly, maybe add this back in later.
                        # This means that we never set the removal date on the OrderGroup when creating it.
                        # if removal_date:
                        #     order_group.end_date = removal_date
                        if seller_product_location.delivery_fee and is_delivery:
                            order_group.delivery_fee = (
                                seller_product_location.delivery_fee
                            )
                        if seller_product_location.removal_fee and is_delivery:
                            order_group.removal_fee = (
                                seller_product_location.removal_fee
                            )

                        if schedule_window:
                            time_slot_name = schedule_window.split(" ")[0]
                            time_slot = TimeSlot.objects.filter(
                                name=time_slot_name
                            ).first()
                            if time_slot:
                                order_group.time_slot = time_slot
                        if project_id:
                            order_group.project_id = project_id

                        # If Junk Removal, then set the Booking removal date to the same as the delivery date (no asset stays on site).
                        if (
                            not main_product.has_rental
                            and not main_product.has_rental_one_step
                            and not main_product.has_rental_multi_step
                        ):
                            order_group.end_date = delivery_date

                        # Update cache
                        order_groups[seller_product_location.id] = order_group
                    else:
                        # Setting the PK to null to create a new object.
                        order_group = order_groups[seller_product_location.id]
                        order_group.pk = None

                    order_group.save()

                    # Check if this is the parent booking or a related booking.
                    if (
                        str(seller_product_location.id)
                        == seller_product_seller_location_id
                    ):
                        parent_booking = order_group
                    else:
                        related_bookings.append(order_group.id)

                    # Create the order (Let submitted on null, this indicates that the order is in the cart)
                    # The first order of an order group always gets the same start and end date.
                    if is_delivery:
                        order_group.create_delivery(
                            delivery_date, schedule_window=schedule_window
                        )
                    else:
                        order_group.create_pickup(
                            delivery_date, schedule_window=schedule_window
                        )

                # Associate related bookings with the parent booking.
                if not parent_booking:
                    raise Exception("Parent booking not found.")

                OrderGroup.objects.filter(
                    id__in=related_bookings,
                ).update(parent_booking=parent_booking)

            messages.success(request, "Successfully added to cart.")

        # Redirect to a success page or the same page to prevent form resubmission
        return HttpResponseRedirect(reverse("customer_cart"))
    elif request.method == "DELETE":
        # Delete the order group and orders.
        order_group_id = request.GET.get("id")
        order_id = request.GET.get("order_id")
        subtotal = request.GET.get("subtotal")
        cart_count = request.GET.get("count")
        customer_price = request.GET.get("price")
        groupcount = request.GET.get("groupcount")
        order_group = (
            OrderGroup.objects.filter(id=order_group_id)
            .prefetch_related("orders", "related_bookings__orders")
            .first()
        )
        has_related = False

        if customer_price:
            customer_price = float(customer_price)
        else:
            customer_price = 0
        # Only delete the single order/transaction, not the entire order group, except if it is the first order.
        order = Order.objects.filter(id=order_id).first()
        if order_group:
            has_related = order_group.related_bookings.exists()
        if order:
            # Order delete will also delete the order group if it is the only order in the group.
            order.delete()
        context["user_address"] = order_group.user_address_id
        if subtotal:
            context["subtotal"] = float(subtotal) - float(customer_price)
        if cart_count:
            context["cart_count"] = int(cart_count) - 1
        if groupcount:
            context["groupcount"] = int(groupcount) - 1
        if order_group:
            messages.success(request, "Order removed from cart.")
        else:
            messages.error(request, f"Order not found [{order_group_id}].")
        if request.headers.get("HX-Request"):
            if has_related:
                # Do a full page reload because multiple items need to disappear from the cart
                response = render(
                    request,
                    "customer_dashboard/new_order/cart_remove_item.html",
                    context,
                )
                response["HX-Refresh"] = "true"
                return response
            return render(
                request,
                "customer_dashboard/new_order/cart_remove_item.html",
                context,
            )

    query_params = request.GET.copy()
    # Load the cart page
    context["subtotal"] = 0
    context["cart_count"] = 0

    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        filter_qry = request.GET.get("filter")
        my_carts = request.GET.get("my_carts")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        if start_date:
            # Parse date object
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            check_date = start_date
        else:
            check_date = timezone.now().date()

        if end_date:
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

        # Pull all orders with submitted_on = None and show them in the cart.
        orders = CartUtils.get_booking_objects(
            request,
            context["user"],
            context["user_group"],
            is_impersonating(request),
        )

        if my_carts:
            context["help_text"] = "My "
            orders = orders.filter(order_group__user_id=context["user"].id)
        else:
            context["help_text"] = "All "

        if filter_qry == "new":
            # Displays all open orders that the Order.CreatedDate == today
            if start_date and end_date:
                # Could use https://docs.djangoproject.com/en/5.0/ref/models/querysets/#range
                orders = orders.filter(
                    Q(created_on__date__gte=start_date)
                    & Q(created_on__date__lte=end_date)
                )
                context["help_text"] += (
                    f"open orders created between {start_date} and {end_date}."
                )
            else:
                orders = orders.filter(created_on__date=check_date)
                if start_date:
                    context["help_text"] += f"open orders created on {start_date}."
                else:
                    context["help_text"] += "open orders created today."
        elif filter_qry == "starting":
            # Displays all open orders that have an Order.EndDate LESS THAN 5 days from Today
            # starting in less than 5 days = starting T + 1-5 .. basically meaning these orders are high priority because it’s coming up on the date
            orders = orders.filter(
                Q(end_date__gte=check_date)
                & Q(end_date__lte=check_date + datetime.timedelta(days=5))
            )
            if start_date:
                context["help_text"] += (
                    f"open orders expiring (Order.EndDate) within 5 days after {check_date}."
                )
            else:
                context["help_text"] += (
                    "open orders expiring (Order.EndDate) within 5 days."
                )
        elif filter_qry == "inactive":
            # Displays all open orders that haven't been updated in GREATER THAN 5 days & today is BEFORE any order's Order.EndDate
            orders = orders.filter(
                Q(updated_on__date__lt=check_date - datetime.timedelta(days=5))
                & Q(end_date__lt=check_date)
            )
            if start_date:
                context["help_text"] += (
                    f"open orders that haven't been updated in more than 5 days & {check_date} is after any order's EndDate."
                )
            else:
                context["help_text"] += (
                    "open orders that haven't been updated in more than 5 days & today is after any order's EndDate."
                )
        elif filter_qry == "expired":
            # Displays all open orders that have an Order.EndDate AFTER Today
            # expired = T - infinite .. basically these are in the last and we will start working to clear this list becuase it’s an error or expired quote now
            orders = orders.filter(end_date__lt=check_date)
            if start_date:
                context["help_text"] += (
                    f"open orders that have an Order.EndDate before {check_date}."
                )
            else:
                context["help_text"] += (
                    "open orders that have an Order.EndDate before Today."
                )
        else:
            # active: default filter. Displays all open orders
            if start_date and end_date:
                orders = orders.filter(
                    Q(end_date__gte=start_date) & Q(end_date__lte=end_date)
                )
                context["help_text"] += (
                    f"open orders starting on or between {start_date} and {end_date}."
                )
            elif start_date:
                orders = orders.filter(end_date__gte=start_date)
                context["help_text"] += (
                    f"open orders starting on or after {start_date}."
                )
            elif end_date:
                orders = orders.filter(end_date__lte=end_date)
                context["help_text"] += (
                    f"open orders starting on or before {start_date}."
                )
            else:
                context["help_text"] += "open orders."

        if not orders:
            # messages.error(request, "Your cart is empty.")
            pass
        else:
            # Get unique order group objects from the orders and place them in address buckets.
            # This code takes the longest to execute.
            context.update(CartUtils.get_cart_orders(orders))

            # get the supplier addresses
            context["seller_addresses"] = []

            # Get the seller price for each order and add it to the context.
            for bucket in context["cart"]:
                bucket["ids"] = []
                bucket["parent_bookings"] = set()
                supplier_total = 0
                # context["cart"][addr]["show_quote"] = True
                checkout_order = None
                for item in bucket["items"]:
                    order = item["order"]
                    bucket["ids"].append(str(order.id))
                    # If the order does not have a parent booking, it is a parent booking.
                    # Add its id to the parent bookings set.
                    if not order.order_group.parent_booking:
                        bucket["parent_bookings"].add(order.order_group_id)

                    if order.checkout_order:
                        checkout_order = order.checkout_order
                    supplier_total += order.seller_price()

                    # START Bundle fees.
                    for line_item in order.order_line_items.filter(
                        order_line_item_type__code="DELIVERY"
                    ):
                        item["delivery_fee"] = line_item.rate
                        break
                    for line_item in order.order_line_items.filter(
                        order_line_item_type__code="REMOVAL"
                    ):
                        item["removal_fee"] = line_item.rate
                        break

                    item["seller_address"] = (
                        order.order_group.seller_product_seller_location.seller_location
                    )
                    if not any(
                        item["seller_address"] == addr["address"]
                        for addr in context["seller_addresses"]
                    ):
                        context["seller_addresses"].append(
                            {"address": item["seller_address"]}
                        )

                    context["seller_addresses"][-1]["seller"] = (
                        order.order_group.seller_product_seller_location.seller_location.seller
                    )
                    # if this address has a bundle give the price
                    if order.order_group.freight_bundle:
                        context["seller_addresses"][-1]["delivery_fee"] = (
                            order.order_group.freight_bundle.delivery_fee
                        )
                        context["seller_addresses"][-1]["removal_fee"] = (
                            order.order_group.freight_bundle.removal_fee
                        )
                    # END Bundle fees.

                if (
                    checkout_order
                    and supplier_total == checkout_order.seller_price
                    and checkout_order.quote_expiration
                ):
                    bucket["quote_sent_on"] = checkout_order.updated_on

        return render(request, "customer_dashboard/new_order/cart_list.html", context)

    context["cart_link"] = f"{reverse('customer_cart')}?{query_params.urlencode()}"
    return render(
        request,
        "customer_dashboard/new_order/cart.html",
        context,
    )


@login_required(login_url="/admin/login/")
def new_bundle(request):
    context = get_user_context(request)
    # save all the bundles being submitted
    if request.user.is_staff:
        if request.method == "POST":
            # get the bundle items
            bundles = request.POST.get("bundles")
            bundles = json.loads(bundles)
            for bundle in bundles:
                # new bundle with using ids passed in the request
                # recreate the order line items with no delivery cost
                # safety checks:
                # 1. there are 2 or more items in the bundle
                # 2. the items are from the same seller address
                # 3. the items are from the same company address
                # 4. the items are not already in a bundle then delete the bundle and create a new one

                if "empty" in bundle:
                    for orderId in bundle["items"]:
                        order = Order.objects.get(id=orderId)
                        if order.order_group.freight_bundle:
                            order.order_group.freight_bundle.delete()
                            break
                else:
                    if len(bundle["items"]) < 2:
                        # if this is a bundle delete it
                        messages.error(request, "Bundle must have at least 2 items.")
                        return HttpResponseRedirect(reverse("customer_cart"))

                    matchSellerAddress = Order.objects.get(
                        id=bundle["items"][0]
                    ).order_group.seller_product_seller_location.seller_location.id
                    for orderId in bundle["items"]:
                        order = Order.objects.get(id=orderId)
                        if (
                            order.order_group.seller_product_seller_location.seller_location.id
                            != matchSellerAddress
                        ):
                            messages.error(
                                request,
                                "Items in bundle must be from the same seller address.",
                            )
                            return HttpResponseRedirect(reverse("customer_cart"))

                    matchCompanyAddress = Order.objects.get(
                        id=bundle["items"][0]
                    ).order_group.user_address.id
                    for orderId in bundle["items"]:
                        order = Order.objects.get(id=orderId)
                        if order.order_group.user_address.id != matchCompanyAddress:
                            messages.error(
                                request,
                                "Items in bundle must be for the same user address.",
                            )
                            return HttpResponseRedirect(reverse("customer_cart"))

                    for orderId in bundle["items"]:
                        order = Order.objects.get(id=orderId)
                        if order.order_group.freight_bundle:
                            old_bundle = order.order_group.freight_bundle
                            # delete will handle recalculating the order line items
                            old_bundle.delete()
                            break
                            # messages.error(request, f"Item {order.id} is already in a bundle.")
                            # return HttpResponseRedirect(reverse("customer_cart"))

                    try:
                        deliveryCost = Decimal(bundle["deliveryCost"])
                    except:
                        deliveryCost = 0
                    try:
                        removalCost = Decimal(bundle["removalCost"])
                    except:
                        removalCost = 0

                    new_bundle = FreightBundle(
                        name="bundle",
                        delivery_fee=deliveryCost,
                        removal_fee=removalCost,
                    )
                    new_bundle.save()
                    # divide the delivery and removal cost among the items
                    # also add the costs to the order_group
                    dividedDeliveryCost = deliveryCost / len(bundle["items"])
                    dividedRemovalCost = removalCost / len(bundle["items"])
                    for orderId in bundle["items"]:
                        order = Order.objects.get(id=orderId)
                        order.order_line_items.all().delete()
                        order.add_line_items(
                            True,
                            custom_delivery_fee=dividedDeliveryCost,
                            custom_removal_fee=dividedRemovalCost,
                        )
                        order.order_group.freight_bundle = new_bundle
                        order.order_group.delivery_fee = dividedDeliveryCost
                        order.order_group.removal_fee = dividedRemovalCost
                        order.order_group.save()
        messages.success(request, "Bundle saved.")
    else:
        messages.error(request, "You do not have permission to save bundles.")
    return HttpResponseRedirect(reverse("customer_cart"))


@login_required(login_url="/admin/login/")
@catch_errors()
def new_order_6(request, order_group_id):
    context = get_user_context(request)
    order_group = OrderGroup.objects.filter(id=order_group_id).first()
    if order_group:
        order_group.delete()
        messages.success(request, "Order removed from cart.")
    else:
        messages.error(request, f"Order not found [{order_group_id}].")
    return HttpResponseRedirect(reverse("customer_home"))


@login_required(login_url="/admin/login/")
def edit_attachments(request, order_group_id):
    context = {}

    if not OrderGroup.objects.filter(id=order_group_id).exists():
        return HttpResponse("Not found", status=404)

    order_group = OrderGroup.objects.get(id=order_group_id)
    OrderGroupAttachmentsFormSet = inlineformset_factory(
        OrderGroup,
        OrderGroupAttachment,
        form=OrderGroupAttachmentsForm,
        formset=MultiTabularFormSet,
        can_delete=True,
        extra=0,
    )

    if request.method == "POST":
        # Edit Attachments
        if "attachments_card" in request.POST:
            attachments_formset = OrderGroupAttachmentsFormSet(
                request.POST, request.FILES, instance=order_group
            )
            if attachments_formset.is_valid():
                if attachments_formset.has_changed():
                    attachments_formset.instance = order_group
                    attachments_formset.save()
                    context["success_text"] = "Attachments saved successfully."
                    # Reinitialize Formset
                    attachments_formset = OrderGroupAttachmentsFormSet(
                        instance=order_group
                    )
                else:
                    context["success_text"] = "No changes detected."
            else:
                messages.error(
                    request,
                    f"Error saving lead {attachments_formset.non_field_errors().as_text()}",
                )
                # lead.refresh_from_db()

            # Reinitialize Form
            # lead_form = LeadDetailForm(instance=lead)
    else:
        attachments_formset = OrderGroupAttachmentsFormSet(instance=order_group)

    context["order_group"] = order_group
    context["attachments_formset"] = attachments_formset

    return render(
        request,
        "customer_dashboard/new_order/cart_order_edit_attachments.html",
        context,
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def show_quote(request):
    context = get_user_context(request)
    quote_id = request.GET.get("quote_id")
    # if quote_id:
    #     checkout_order = CheckoutOrder.objects.get(id=quote_id)
    #     payload = {"trigger": checkout_order.quote}
    # else:
    order_id_lst = ast.literal_eval(request.GET.get("ids"))
    checkout_order = QuoteUtils.create_quote(order_id_lst, None, quote_sent=False)
    payload = {"trigger": checkout_order.get_quote()}
    payload["trigger"]["accept_url"] = f"{settings.DASHBOARD_BASE_URL}/customer/cart/"
    return render(request, "customer_dashboard/customer_quote.html", payload)


@login_required(login_url="/admin/login/")
def cart_send_quote(request):
    context = get_user_context(request)
    if request.method == "POST":
        # Get json body
        try:
            data = json.loads(request.body)
            email_lst = list(set(data.get("emails")))
            to_emails = ",".join(email_lst)
            order_id_lst = data.get("ids")
            if email_lst and order_id_lst:
                checkout_order = QuoteUtils.create_quote(
                    order_id_lst, email_lst, quote_sent=True
                )
                data = {
                    "transactional_message_id": 4,
                    "subject": checkout_order.subject,
                    "message_data": checkout_order.get_quote(),
                    "reply_to": request.user.email,
                }
                data["message_data"]["accept_url"] = (
                    f"{settings.DASHBOARD_BASE_URL}/customer/cart/"
                )
                # https://customer.io/docs/api/app/#operation/sendEmail
                headers = {
                    "Authorization": f"Bearer {settings.CUSTOMER_IO_API_KEY}",
                    "Content-Type": "application/json",
                }
                ret_data = []
                had_error = False
                # https://customer.io/docs/journeys/liquid-tag-list/?version=latest
                # for email in email_lst:
                data["to"] = to_emails
                data["identifiers"] = {"email": email_lst[0]}

                json_data = json.dumps(data, cls=DecimalEncoder)
                response = requests.post(
                    "https://api.customer.io/v1/send/email",
                    headers=headers,
                    data=json_data,
                )
                if response.status_code < 400:
                    ret_data.append(f"Quote sent to {to_emails}.")
                    # resp_json = response.json()
                    # [delivery_id:{resp_json['delivery_id']}-queued_at:{resp_json['queued_at']}]
                else:
                    had_error = True
                    resp_json = response.json()
                    ret_data.append(
                        f"Error sending quote to {to_emails} [{resp_json['meta']['error']}]"
                    )
                if had_error:
                    return JsonResponse(
                        {"status": "error", "error": " | ".join(ret_data)}
                    )
                return JsonResponse(
                    {"status": "success", "message": " | ".join(ret_data)}
                )
            else:
                return JsonResponse(
                    {"status": "error", "error": "No email or order ids."}
                )
        except Exception as e:
            logger.error(f"Error sending quote: {e}")
            return JsonResponse({"status": "error", "error": str(e)})
    return HttpResponse(status=204)


@login_required(login_url="/admin/login/")
def make_payment_method_default(request, user_address_id, payment_method_id):
    context = get_user_context(request)
    if request.method == "POST":
        context["forloop"] = {"counter": request.POST.get("loopcount", 0)}
        if request.POST.get("is_checkout"):
            context["is_checkout"] = 1
        else:
            context["is_checkout"] = 0
        # user_address_id = request.POST.get("user_address")
        # payment_method_id = request.POST.get("payment_method")
        context["payment_method"] = PaymentMethod.objects.filter(
            id=payment_method_id
        ).first()
        context["user_address"] = UserAddress.objects.filter(id=user_address_id).first()
        if context["payment_method"] and context["user_address"]:
            context["user_address"].default_payment_method_id = context[
                "payment_method"
            ].id
            context["user_address"].save()
            setattr(context["payment_method"], "is_default", True)

        return render(
            request, "customer_dashboard/snippets/payment_method_item.html", context
        )
    else:
        return HttpResponse(status=204)


@login_required(login_url="/admin/login/")
def update_payment_method_status(request, payment_method_id):
    context = get_user_context(request)
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to update PaymentMethod.")
        return HttpResponse("Unauthorized", status=401)
    if request.method == "POST":
        context["forloop"] = {"counter": request.POST.get("loopcount", 0)}
        if request.POST.get("is_checkout"):
            context["is_checkout"] = 1
        else:
            context["is_checkout"] = 0
        # payment_method_id = request.POST.get("payment_method")
        context["payment_method"] = PaymentMethod.objects.filter(
            id=payment_method_id
        ).first()
        if context["payment_method"]:
            context["payment_method"].active = True
            context["payment_method"].save()
        return render(
            request, "customer_dashboard/snippets/payment_method_item.html", context
        )
    else:
        return HttpResponse(status=204)


@login_required(login_url="/admin/login/")
def remove_payment_method(request, payment_method_id):
    context = get_user_context(request)
    http_status = 204
    status_text = ""
    if request.method == "POST":
        payment_method = PaymentMethod.objects.filter(id=payment_method_id).first()
        if payment_method:
            try:
                payment_method.delete()
                http_status = 200
            except Exception as e:
                http_status = 400
                status_text = f"Error deleting payment method: {e}"
        else:
            http_status = 400
            status_text = "Payment method not found."

    return HttpResponse(status=http_status, content=status_text)


@login_required(login_url="/admin/login/")
def add_payment_method(request):
    context = get_user_context(request)
    http_status = 204
    status_text = ""
    # TODO: Make user_group optional
    if request.method == "POST":
        user_address_id = request.POST.get("user_address")
        user_group_id = request.POST.get("user_group")
        if user_address_id:
            context["user_address"] = UserAddress.objects.filter(
                id=user_address_id
            ).first()
        # If staff, then always get the user and user_group from POST parameters.
        if request.user.is_staff:
            if user_address_id:
                context["user_group"] = context["user_address"].user_group
            else:
                context["user_group"] = UserGroup.objects.filter(
                    id=user_group_id
                ).first()
            # If context["user"].user_group_id is user_group_id,
            # then use context["user"], else get the first user in the user group.
            if context["user"].user_group:
                if str(context["user"].user_group_id) != str(user_group_id):
                    context["user"] = (
                        context["user_group"].users.filter(type=UserType.ADMIN).first()
                    )
            else:
                context["user"] = (
                    context["user_group"].users.filter(type=UserType.ADMIN).first()
                )
            if not context["user"]:
                context["user"] = context["user_group"].users.first()
        token = request.POST.get("token")
        if token:
            if context["user"] and context["user_group"]:
                # Check if the payment method already exists by token.
                payment_method = PaymentMethod.objects.filter(token=token).first()
                if payment_method:
                    status_text = "This card number is already associated with a saved payment method. To proceed, please use a different card or delete the existing card if only modifying the expiration date or CVV."
                    http_status = 400
                else:
                    payment_method = PaymentMethod(
                        user=context["user"],
                        user_group=context["user_group"],
                        token=token,
                    )
                    payment_method.save()
                    if user_address_id:
                        context[
                            "user_address"
                        ].default_payment_method_id = payment_method.id
                        context["user_address"].save()
                    messages.success(request, "Payment method added.")
                    http_status = 201
            else:
                if not context["user"]:
                    status_text = "Unable to save card. User not found."
                elif not context["user_group"]:
                    status_text = "Unable to save card. Company not found."
                http_status = 400

    return HttpResponse(status=http_status, content=status_text)


@login_required(login_url="/admin/login/")
@catch_errors()
def checkout_terms_agreement(request, user_address_id):
    context = get_user_context(request)
    context["user_address"] = UserAddress.objects.filter(id=user_address_id).first()
    context["help_msg"] = ""
    context["css_class"] = "form-valid"
    # Get all orders in the cart for this user_address_id.
    orders = context["user_address"].get_cart()
    context["orders"] = orders
    if request.method == "POST":
        for order in orders:
            if not order.order_group.is_agreement_signed:
                order.order_group.agreement_signed_by = context["user"]
                order.order_group.agreement_signed_on = timezone.now()
                order.order_group.save()
        context["show_success"] = True

    return render(
        request,
        "customer_dashboard/snippets/terms_agreement_form.html",
        context,
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def credit_application(request):
    context = get_user_context(request)
    redirect_url = request.GET.get("return_to", None)
    if redirect_url:
        request.session["credit_application_return_to"] = redirect_url
    if not context["user_group"]:
        messages.error(
            request,
            "Unfortunately, we could not find your company in our system. Please contact us.",
        )
        # customer_credit_application
        return HttpResponseRedirect(reverse("customer_cart"))
    user_group_legal = UserGroupLegal.objects.filter(
        user_group_id=context["user_group"].id
    ).first()

    if request.method == "POST":
        try:
            form = CreditApplicationForm(request.POST, request.FILES)
            context["form"] = form
            if context["form"].is_valid():
                accepts_terms = form.cleaned_data.get("accepts_terms")
                if not accepts_terms:
                    messages.error(
                        request,
                        "Please accept the Terms and Conditions to authorize a credit check.",
                    )
                    return render(
                        request, "customer_dashboard/credit_application.html", context
                    )
                # Create or Update UserGroupLegal
                save_user_group_legal = False
                if not user_group_legal:
                    user_group_legal = UserGroupLegal(
                        user_group=context["user_group"], country="US"
                    )
                    save_user_group_legal = True
                if (
                    form.cleaned_data.get("structure")
                    and form.cleaned_data.get("structure") != user_group_legal.structure
                ):
                    user_group_legal.structure = form.cleaned_data.get("structure")
                    save_user_group_legal = True
                if (
                    form.cleaned_data.get("tax_id")
                    and form.cleaned_data.get("tax_id") != user_group_legal.tax_id
                ):
                    user_group_legal.tax_id = form.cleaned_data.get("tax_id")
                    save_user_group_legal = True
                if (
                    form.cleaned_data.get("legal_name")
                    and form.cleaned_data.get("legal_name") != user_group_legal.name
                ):
                    user_group_legal.name = form.cleaned_data.get("legal_name")
                    save_user_group_legal = True
                if (
                    form.cleaned_data.get("doing_business_as")
                    and form.cleaned_data.get("doing_business_as")
                    != user_group_legal.doing_business_as
                ):
                    user_group_legal.doing_business_as = form.cleaned_data.get(
                        "doing_business_as"
                    )
                    save_user_group_legal = True
                if (
                    form.cleaned_data.get("industry")
                    and form.cleaned_data.get("industry") != user_group_legal.industry
                ):
                    user_group_legal.industry = form.cleaned_data.get("industry")
                    save_user_group_legal = True
                if (
                    form.cleaned_data.get("years_in_business")
                    and form.cleaned_data.get("years_in_business")
                    != user_group_legal.years_in_business
                ):
                    user_group_legal.years_in_business = form.cleaned_data.get(
                        "years_in_business"
                    )
                    save_user_group_legal = True
                if (
                    form.cleaned_data.get("street")
                    and form.cleaned_data.get("street") != user_group_legal.street
                ):
                    user_group_legal.street = form.cleaned_data.get("street")
                    save_user_group_legal = True
                if (
                    form.cleaned_data.get("city")
                    and form.cleaned_data.get("city") != user_group_legal.city
                ):
                    user_group_legal.city = form.cleaned_data.get("city")
                    save_user_group_legal = True
                if (
                    form.cleaned_data.get("state")
                    and form.cleaned_data.get("state") != user_group_legal.state
                ):
                    user_group_legal.state = form.cleaned_data.get("state")
                    save_user_group_legal = True
                if (
                    form.cleaned_data.get("postal_code")
                    and form.cleaned_data.get("postal_code")
                    != user_group_legal.postal_code
                ):
                    user_group_legal.postal_code = form.cleaned_data.get("postal_code")
                    save_user_group_legal = True
                if save_user_group_legal:
                    user_group_legal.save()

                user_group_credit_application = UserGroupCreditApplication(
                    user_group=context["user_group"],
                    estimated_monthly_revenue=form.cleaned_data.get(
                        "estimated_monthly_revenue"
                    ),
                    estimated_monthly_spend=form.cleaned_data.get(
                        "estimated_monthly_spend"
                    ),
                )
                if form.cleaned_data.get("increase_credit"):
                    if context["user_group"].credit_line_limit:
                        requested_credit_limit = context["user_group"].credit_line_limit
                    requested_credit_limit += form.cleaned_data.get("increase_credit")
                    user_group_credit_application.requested_credit_limit = (
                        requested_credit_limit
                    )
                user_group_credit_application.save()
                messages.success(
                    request,
                    'Thank you for your application! Our team will review and reach out once we have a decision in the next 24-48 hours. If you need this booking sooner please use the "Pay Now" button.',
                )
                redirect_url = request.session.get(
                    "credit_application_return_to", reverse("customer_companies")
                )
                if "credit_application_return_to" in request.session:
                    del request.session["credit_application_return_to"]
                return HttpResponseRedirect(redirect_url)
            else:
                # This will let bootstrap know to highlight the fields with errors.
                for field in form.errors:
                    form[field].field.widget.attrs["class"] += " is-invalid"
                messages.error(
                    request, "Error saving, please contact us if this continues."
                )
        except Exception as e:
            messages.error(
                request, f"Error saving, please contact us if this continues. [{e}]"
            )
            logger.error(f"credit_application: [{e}]", exc_info=e)
    else:
        credit_application = (
            context["user_group"].credit_applications.order_by("-created_on").first()
        )
        allow_increase = False
        if (
            context["user_group"].credit_line_limit
            and context["user_group"].credit_line_limit != 0
        ):
            # Allow credit increase
            allow_increase = True
        initial_data = {}
        if credit_application:
            initial_data["estimated_monthly_revenue"] = (
                credit_application.estimated_monthly_revenue
            )
            initial_data["estimated_monthly_spend"] = (
                credit_application.estimated_monthly_spend
            )

        if user_group_legal:
            initial_data["structure"] = user_group_legal.structure
            initial_data["tax_id"] = user_group_legal.tax_id
            initial_data["legal_name"] = user_group_legal.name
            initial_data["doing_business_as"] = user_group_legal.doing_business_as
            initial_data["industry"] = user_group_legal.industry
            initial_data["years_in_business"] = user_group_legal.years_in_business
            initial_data["street"] = user_group_legal.street
            initial_data["city"] = user_group_legal.city
            initial_data["state"] = user_group_legal.state
            initial_data["postal_code"] = user_group_legal.postal_code
        context["form"] = CreditApplicationForm(
            initial=initial_data,
            allow_increase=allow_increase,
        )

    return render(request, "customer_dashboard/credit_application.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def checkout(request, user_address_id):
    context = get_user_context(request)
    context["user_address"] = UserAddress.objects.filter(id=user_address_id).first()
    context["is_checkout"] = 1
    # Get all orders in the cart for this user_address_id.
    orders = context["user_address"].get_cart()
    context["orders"] = orders
    if context["user_group"]:
        context["credit_application"] = (
            context["user_group"].credit_applications.order_by("-created_on").first()
        )

    if request.method == "POST":
        if not is_impersonating(request):
            for order in orders:
                if not order.order_group.is_agreement_signed:
                    # NOTE: Sign the agreement with signed in user, no impersonation allowed.
                    order.order_group.agreement_signed_by = request.user
                    order.order_group.agreement_signed_on = timezone.now()
                    order.order_group.save()
        # Save access details to the user address.
        payment_method_id = request.POST.get("payment_method")
        if payment_method_id:
            if payment_method_id == "paylater":
                payment_method_id = None
            try:
                CheckoutUtils.checkout(
                    context["user_address"], orders, payment_method_id
                )
                messages.success(request, "Successfully checked out!")
                return HttpResponseRedirect(reverse("customer_cart"))
            except CardError as e:
                messages.error(
                    request, f"Error processing payment: {e.code}-[{e.param}]"
                )
                context["form_error"] = e.message
            except ValidationError as e:
                messages.error(request, e.message)
                context["form_error"] = e.message
        else:
            messages.error(request, "No payment method selected.")
            context["form_error"] = "No payment method selected."
        if request.POST.get("access_details") != context["user_address"].access_details:
            context["user_address"].access_details = request.POST.get("access_details")
            context["user_address"].save()
            messages.success(request, "Access details saved.")

    context["cart"] = []
    context["discounts"] = 0
    context["subtotal"] = 0
    context["cart_count"] = 0
    context["pre_tax_subtotal"] = 0
    if context["user_group"]:
        payment_methods = PaymentMethod.objects.filter(
            user_group_id=context["user_group"].id
        )
    else:
        if context["user_address"].user_group_id:
            payment_methods = PaymentMethod.objects.filter(
                user_group_id=context["user_address"].user_group_id
            )
        elif context["user_address"].user_id:
            payment_methods = PaymentMethod.objects.filter(
                user_id=context["user_address"].user_id
            )
        else:
            payment_methods = PaymentMethod.objects.filter(user_id=context["user"].id)
    # Order payment methods by newest first.
    payment_methods = payment_methods.order_by("-created_on")
    context["payment_methods"] = []
    for payment_method in payment_methods:
        if payment_method.id == context["user_address"].default_payment_method_id:
            setattr(payment_method, "is_default", True)
        context["payment_methods"].append(payment_method)
    context["needs_approval"] = False
    order_id_lst = []
    context["estimated_taxes"] = 0
    context["total"] = 0
    context["show_terms"] = False
    context["is_first_order"] = False
    context["contains_pickup_order"] = False
    for order in orders:
        if order.status == Order.Status.ADMIN_APPROVAL_PENDING:
            context["needs_approval"] = True
        if not order.order_group.is_agreement_signed:
            context["show_terms"] = True
        if (
            order.order_type == Order.Type.DELIVERY
            or order.order_type == Order.Type.PICKUP
            or order.order_type == Order.Type.ONE_TIME
        ):
            context["is_first_order"] = True
        customer_price = order.customer_price()
        customer_price_full = order.full_price()
        context["subtotal"] += customer_price_full
        context["pre_tax_subtotal"] += customer_price
        price_data = order.get_price()
        context["cart"].append(
            {
                "order": order,
                "order_group": order.order_group,
                "price": customer_price,
                "count": 1,
                "order_type": order.order_type,
                "price_data": price_data,
            }
        )
        context["estimated_taxes"] += price_data["tax"]
        context["total"] += price_data["total"]
        context["cart_count"] += 1
        order_id_lst.append(order.id)
        if not order.order_group.is_delivery:
            context["contains_pickup_order"] = True

    context["discounts"] = context["subtotal"] - context["pre_tax_subtotal"]
    if not context["cart"]:
        messages.error(request, "This Order is empty.")
        return HttpResponseRedirect(reverse("customer_cart"))
    return render(
        request,
        "customer_dashboard/new_order/checkout.html",
        context,
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def profile(request):
    context = get_user_context(request)
    user = context["user"]

    if request.method == "POST":
        # NOTE: Since email is disabled, it is never POSTed,
        # so we need to copy the POST data and add the email back in. This ensures its presence in the form.
        POST_COPY = request.POST.copy()
        POST_COPY["email"] = user.email
        form = UserForm(POST_COPY, request.FILES, instance=user, auth_user=request.user)
        context["form"] = form
        if form.is_valid():
            if form.has_changed():
                form.save()
                context["user"] = user
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            # Reload the form with the updated data (for some reason it doesn't update the form with the POST data).
            form = UserForm(instance=user, auth_user=request.user)
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
        form = UserForm(instance=user, auth_user=request.user)
        context["form"] = form
    return render(request, "customer_dashboard/profile.html", context)


@login_required(login_url="/admin/login/")
def order_group_swap(request, order_group_id, is_removal=False):
    context = get_user_context(request)

    order_group = OrderGroup.objects.filter(id=order_group_id).first()
    context["order_group"] = order_group
    context["is_removal"] = is_removal
    if is_removal:
        context["submit_link"] = reverse(
            "customer_order_group_removal",
            kwargs={
                "order_group_id": order_group_id,
            },
        )
    else:
        context["submit_link"] = reverse(
            "customer_order_group_swap",
            kwargs={
                "order_group_id": order_group_id,
            },
        )

    if request.method == "POST":
        try:
            form = OrderGroupSwapForm(
                request.POST,
                request.FILES,
                auth_user=request.user,
                is_removal=is_removal,
            )
            context["form"] = form
            if form.is_valid():
                swap_date = form.cleaned_data.get("swap_date")
                schedule_window = form.cleaned_data.get("schedule_window")
                # is_removal = form.cleaned_data.get("is_removal")
                # Create the Order object.
                if is_removal:
                    order_group.create_removal(swap_date, schedule_window)
                else:
                    order_group.create_swap(swap_date, schedule_window)
                # Add response header to let HTMX know to redirect to the cart page.
                response = HttpResponse("", status=201)
                response["HX-Redirect"] = reverse("customer_cart")
                context["form_msg"] = "Successfully saved!"
                messages.success(request, "Successfully added to cart!")
                return response
            else:
                raise InvalidFormError(form, "Invalid UserInviteForm")
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
        except ValidationError as e:
            context["form_error"] = " | ".join(e.messages)
            logger.error(
                f"order_group_swap:ValidationError: [{order_group_id}]-[{is_removal}]-[{request.POST}]-[{e.messages}]",
                exc_info=e,
            )
        except Exception as e:
            context["form_error"] = (
                f"Error saving, please contact us if this continues: [{e}]."
            )
            logger.error(
                f"order_group_swap: [{order_group_id}]-[{is_removal}]-[{request.POST}]-[{e}]",
                exc_info=e,
            )
    else:
        context["form"] = OrderGroupSwapForm(
            initial={
                "order_group_id": order_group.id,
                "order_group_start_date": order_group.start_date,
            },
            auth_user=request.user,
            is_removal=is_removal,
        )

    return render(request, "customer_dashboard/snippets/order_group_swap.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
@require_POST
def order_review_swap(request):
    """
    Handle the swapping of an order review rating.

    This view handles POST requests to update the rating of an order review.
    It ensures that the request contains the necessary data and that the review
    can only be updated within 10 minutes of its creation.

    Args:
        request (HttpRequest): The HTTP request object containing POST data. Should include `order_id` and `rating`.

    Returns:
        HttpResponse: A response object with the rendered form template or an error message.
    """
    # The request to this url must be POST
    order_id = request.POST.get("order_id")
    rating = request.POST.get("rating")

    if not order_id or not rating:
        return HttpResponse(content={"error": "Missing required post data"}, status=400)

    rating = bool(int(rating))
    order = Order.objects.select_related("review").get(id=order_id)

    if not hasattr(order, "review"):
        review = OrderReview(order=order, rating=rating)
        review.save()
    elif (timezone.now() - order.review.created_on).total_seconds() > 60 * 10:
        # Prevent review from updating if it has been more than 10 minutes.
        return HttpResponse(
            content={"error": "Review cannot be updated after 10 minutes."}, status=400
        )
    elif order.review.rating != rating:
        order.review.rating = rating
        order.review.save()

    formset = OrderReviewFormSet(instance=order, initial={"rating": rating})
    context = {"formset": formset, "order": order}

    return render(
        request, "customer_dashboard/snippets/order_review_form.html", context
    )


@login_required(login_url="/admin/login/")
@catch_errors()
@require_POST
def order_review_form(request):
    """
    Handle the submission of the order review form.

    This view handles POST requests to submit the order review form. It ensures
    that the review can only be updated within 10 minutes of its creation and
    saves the form data if it is valid and has changed.

    Args:
        request (HttpRequest): The HTTP request object containing POST data.

    Returns:
        HttpResponseRedirect: A redirect response to the order group detail page.
    """
    # The request to this url must be POST
    rating = request.POST.get("rating")
    order_id = request.POST.get("order_id")
    order = Order.objects.get(id=order_id)
    formset = OrderReviewFormSet(
        request.POST, instance=order, initial={"rating": rating}
    )

    if (timezone.now() - order.review.created_on).total_seconds() > 60 * 10:
        # Prevent review from updating if it has been more than 10 minutes.
        messages.error("Review cannot be updated after 10 minutes.")
    elif formset.is_valid():
        # Check if any changes to form were made
        if formset.has_changed():
            formset.save()
            messages.success(request, "Successfully saved!")
        else:
            messages.info(request, "No changes detected.")

    return HttpResponseRedirect(
        reverse(
            "customer_order_group_detail",
            kwargs={"order_group_id": order.order_group_id},
        )
    )


@login_required(login_url="/admin/login/")
def bookings_page_settings(request):
    # context = get_user_context(request)
    http_status = 204
    status_text = ""
    if request.method == "POST":
        column = request.POST.get("column")
        is_checked = request.POST.get("is_checked")
        if is_checked == "true":
            is_checked = True
        else:
            is_checked = False
        session_key = f"bookings_page_settings_{column}"
        request.session[session_key] = is_checked
        request.session.save()
        http_status = 200
    return HttpResponse(status=http_status, content=status_text)


@login_required(login_url="/admin/login/")
@catch_errors()
def order_groups(request):
    context = get_user_context(request)
    pagination_limit = 10
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    date = request.GET.get("date", None)
    location_id = request.GET.get("location_id", None)
    user_id = request.GET.get("user_id", None)

    query_params = request.GET.copy()
    is_active = request.GET.get("active")
    context["is_active"] = is_active == "on"

    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        my_accounts = request.GET.get("my_accounts")
        search_q = request.GET.get("q", None)

        if user_id:
            order_groups = OrderGroup.objects.filter(user_id=user_id)
        else:
            order_groups = get_order_group_objects(
                request, context["user"], context["user_group"]
            )

        if my_accounts:
            order_groups = order_groups.filter(
                user_address__user_group__account_owner_id=request.user.id
            )

        if search_q:
            # order_group.seller_product_seller_location.seller_location.name
            order_groups = order_groups.filter(
                Q(user_address__name__icontains=search_q)
                | Q(
                    seller_product_seller_location__seller_location__name__icontains=search_q
                )
                | Q(user_address__street__icontains=search_q)
                | Q(user_address__city__icontains=search_q)
                | Q(user_address__state__icontains=search_q)
                | Q(user_address__postal_code__icontains=search_q)
                | Q(user_address__project_id__icontains=search_q)
                | Q(project_id__icontains=search_q)
            )

        if date:
            order_groups = order_groups.filter(end_date=date)
        if location_id:
            # TODO: Ask if location is user_address_id or seller_product_seller_location__seller_location_id
            order_groups = order_groups.filter(user_address_id=location_id)

        # Select only order_groups where the last order.submitted_on is not null.
        order_groups = order_groups.annotate(
            # Using subquery so future annotations are not messed up.
            last_order_submitted_on=Subquery(
                Order.objects.filter(order_group=OuterRef("pk"))
                .order_by("-submitted_on")
                .values("submitted_on")[:1]
            )
        ).filter(last_order_submitted_on__isnull=False)

        # Active orders are those that have an end_date in the future or are null (recurring orders).
        # if is_active: then only show order_groups where end_date is in the future or is null.
        if is_active:
            order_groups = order_groups.filter(
                Q(end_date__isnull=True) | Q(end_date__gte=datetime.date.today())
            )
        else:
            order_groups = order_groups.filter(
                Q(end_date__isnull=False) & Q(end_date__lt=datetime.date.today())
            )

        # Select related fields to reduce db queries.
        order_groups = (
            order_groups.select_related(
                "seller_product_seller_location__seller_location",
                "seller_product_seller_location__seller_product__seller",
                "seller_product_seller_location__seller_product__product__main_product__main_product_category",
                "user_address__user__user_group__account_owner",
            )
            .prefetch_related(
                "orders__order_line_items",
                "seller_product_seller_location__seller_product__product__main_product__images",
                "related_bookings",
            )
            .with_nearest_orders()
        )

        # Get the order groups and group them by user_address.
        # Query a list of addresses with the count of bookings for each address.
        addresses = list(
            UserAddress.objects.filter(order_groups__id__in=order_groups)
            .annotate(
                count=Count("order_groups", distinct=True),
                end_date=Max("order_groups__end_date"),
            )
            .order_by("-end_date")
            .values_list("id", "count")
        )
        # Paginate responses by UserAddress before making db queries.
        paginator = Paginator(addresses, pagination_limit)
        page_obj = paginator.get_page(page_number)
        context["page_obj"] = page_obj

        # Create a dictionary to map addresses to their order in page_obj.
        address_order = {
            add[0]: {
                "count": add[1],
                "index": index,
            }
            for index, add in enumerate(page_obj)
        }

        # Filter down the order groups to only those in the current page.
        order_groups = order_groups.filter(
            user_address__in=address_order.keys()
        ).order_by("user_address")

        # Construct the order groups list.
        booking_groups = []
        for address, items in groupby(order_groups, key=attrgetter("user_address")):
            bucket = {
                "r0": {},
                "nr": [],
                "user_address": address,
                "count": address_order[address.id]["count"],
            }
            # Create two lists in the bucket: One for Non-Related orders and one for Parent Orders (R0, like root).
            # Sort the order groups by the number of related bookings, so that the most related bookings are displayed first.
            # As a bonus we know that related bookings will always be after their parent booking in the iteration.
            for order_group in sorted(
                items,
                key=lambda x: x.related_bookings.count()
                if hasattr(x, "related_bookings")
                else 0,
                reverse=True,
            ):
                if (
                    not order_group.parent_booking
                    and order_group.related_bookings.exists()
                ):
                    # These will be displayed with all related orders underneath.
                    bucket["r0"][order_group.id] = {
                        "order_group": order_group,
                        "related": [],
                    }
                elif not order_group.parent_booking or not bucket["r0"].get(
                    order_group.parent_booking_id
                ):
                    # Booking is not related to any other booking in this list.
                    bucket["nr"].append(order_group)
                else:
                    # Add the related booking to the parent booking.
                    bucket["r0"][order_group.parent_booking_id]["related"].append(
                        order_group
                    )
            booking_groups.append(bucket)

        context["bookings"] = sorted(
            booking_groups, key=lambda x: address_order[x["user_address"].id]["index"]
        )

        if page_number is None:
            page_number = 1
        else:
            page_number = int(page_number)

        query_params["p"] = 1
        context["page_start_link"] = (
            f"{reverse('customer_order_groups')}?{query_params.urlencode()}"
        )
        query_params["p"] = page_number
        context["page_current_link"] = (
            f"{reverse('customer_order_groups')}?{query_params.urlencode()}"
        )
        if page_obj.has_previous():
            query_params["p"] = page_obj.previous_page_number()
            context["page_prev_link"] = (
                f"{reverse('customer_order_groups')}?{query_params.urlencode()}"
            )
        if page_obj.has_next():
            query_params["p"] = page_obj.next_page_number()
            context["page_next_link"] = (
                f"{reverse('customer_order_groups')}?{query_params.urlencode()}"
            )
        query_params["p"] = paginator.num_pages
        context["page_end_link"] = (
            f"{reverse('customer_order_groups')}?{query_params.urlencode()}"
        )

        return render(
            request, "customer_dashboard/snippets/order_groups_list.html", context
        )
    else:
        if query_params.get("active") is None:
            query_params["active"] = "on"
        if request.user.is_staff and not is_impersonating(request):
            if query_params.get("my_accounts") is None:
                query_params["my_accounts"] = "on"
        context["active_orders_link"] = (
            f"{reverse('customer_order_groups')}?{query_params.urlencode()}"
        )
        return render(request, "customer_dashboard/order_groups.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def order_group_detail(request, order_group_id):
    context = get_user_context(request)
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

    OrderGroupAttachmentsFormSet = inlineformset_factory(
        OrderGroup,
        OrderGroupAttachment,
        form=OrderGroupAttachmentsForm,
        formset=HiddenDeleteFormSet,
        can_delete=True,
        extra=0,
    )

    # Get the time since the order was reviewed to prevent old reviews from being changed
    current_time = timezone.now()
    context["orders"] = (
        order_group.orders.all()
        .annotate(
            time_since_review=ExpressionWrapper(
                current_time - F("review__created_on"), output_field=DurationField()
            ),
        )
        .order_by("-end_date")
    )

    if request.method == "POST":
        try:
            save_model = None
            if "access_details_button" in request.POST:
                context["placement_form"] = PlacementDetailsForm(
                    initial={
                        "placement_details": order_group.placement_details,
                        "delivered_to_street": order_group.delivered_to_street,
                    }
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
                    initial={
                        "access_details": user_address.access_details,
                        "delivered_to_street": order_group.delivered_to_street,
                    }
                )
                form = PlacementDetailsForm(request.POST)
                context["placement_form"] = form
                attachments_formset = OrderGroupAttachmentsFormSet(
                    request.POST, request.FILES, instance=order_group
                )
                if attachments_formset.is_valid():
                    if attachments_formset.has_changed():
                        attachments_formset.instance = order_group
                        attachments_formset.save()
                        save_model = order_group
                if form.is_valid():
                    if (
                        form.cleaned_data.get("placement_details")
                        != order_group.placement_details
                    ):
                        order_group.placement_details = form.cleaned_data.get(
                            "placement_details"
                        )
                        save_model = order_group
                    if (
                        form.cleaned_data.get("delivered_to_street")
                        != order_group.delivered_to_street
                    ):
                        order_group.delivered_to_street = form.cleaned_data.get(
                            "delivered_to_street"
                        )
                        save_model = order_group
                else:
                    for formy in attachments_formset.forms:
                        print(formy.errors)
                    raise InvalidFormError(form, "Invalid PlacementDetailsForm")
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            context["attachments_formset"] = OrderGroupAttachmentsFormSet(
                instance=order_group
            )
            return render(
                request, "customer_dashboard/order_group_detail.html", context
            )
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
            # messages.error(request, e.msg)
    else:
        context["access_form"] = AccessDetailsForm(
            initial={"access_details": user_address.access_details}
        )
        context["placement_form"] = PlacementDetailsForm(
            initial={
                "placement_details": order_group.placement_details,
                "delivered_to_street": order_group.delivered_to_street,
            }
        )
        context["attachments_formset"] = OrderGroupAttachmentsFormSet(
            instance=order_group
        )

    return render(request, "customer_dashboard/order_group_detail.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def order_detail(request, order_id):
    context = get_user_context(request)
    is_line_item = request.GET.get("line_item", None)
    if is_line_item:
        order_line_item = OrderLineItem.objects.filter(id=order_id)
        order_line_item = order_line_item.select_related(
            "order__order_group__seller_product_seller_location__seller_product__seller",
            "order__order_group__user_address",
            "order__order_group__user",
            "order__order_group__seller_product_seller_location__seller_product__product__main_product",
        )
        order_line_item = order_line_item.prefetch_related(
            "order__payouts", "order__order_line_items"
        )
        context["order"] = order_line_item.first().order
    else:
        order = Order.objects.filter(id=order_id)
        order = order.select_related(
            "order_group__seller_product_seller_location__seller_product__seller",
            "order_group__user_address",
            "order_group__user",
            "order_group__seller_product_seller_location__seller_product__product__main_product",
        )
        order = order.prefetch_related("payouts", "order_line_items")
        context["order"] = order.first()
    context["invoices"] = context["order"].get_invoices()

    return render(request, "customer_dashboard/order_detail.html", context)


@login_required(login_url="/admin/login/")
def company_last_order(request):
    context = {}
    user_address_id = request.GET.get("user_address_id", None)
    user_group_id = request.GET.get("user_group_id", None)
    user_id = request.GET.get("user_id", None)
    if user_address_id:
        orders = Order.objects.filter(order_group__user_address_id=user_address_id)
    elif user_group_id:
        orders = Order.objects.filter(order_group__user__user_group_id=user_group_id)
    elif user_id:
        orders = Order.objects.filter(order_group__user_id=user_id)
    else:
        return HttpRequest(status=204)

    orders = orders.order_by("-end_date").first()
    context["last_order"] = orders
    # Assume htmx request, so only return html snippet
    return render(
        request, "customer_dashboard/snippets/company_last_order_col.html", context
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def locations(request):
    context = get_user_context(request)
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    search_q = request.GET.get("q", None)
    # location_id = request.GET.get("location_id", None)
    # This is an HTMX request, so respond with html snippet
    # TODO: Show all locations everyone, but only show the edit button for Admins or locations that the user has access.
    if request.headers.get("HX-Request"):
        tab = request.GET.get("tab", None)
        context["tab"] = tab
        query_params = request.GET.copy()

        account_filter = request.GET.get("account_filter", None)
        account_owner_id = None
        if request.user.is_staff and account_filter == "my_accounts":
            account_owner_id = request.user.id

        if request.user.is_staff and tab == "new":
            user_addresses = UserAddressUtils.get_new(
                search_q=search_q, owner_id=account_owner_id
            )
            context["help_text"] = "New locations created in the last 30 days."
        elif request.user.is_staff and tab == "active":
            user_addresses = UserAddressUtils.get_active(
                search_q=search_q, owner_id=account_owner_id
            )
            context["help_text"] = "Active locations with orders in the last 30 days."
            pagination_limit = 100  # Create large limit due to long request time
        elif request.user.is_staff and (tab == "churned" or tab == "fully_churned"):
            cutoff_date = datetime.date.today() - datetime.timedelta(days=30)
            churn_date = datetime.date.today() - datetime.timedelta(days=60)
            user_addresses = UserAddressUtils.get_churning(
                search_q=search_q,
                tab=tab,
                old_date=churn_date,
                new_date=cutoff_date,
                owner_id=account_owner_id,
            )
            pagination_limit = 200  # Create large limit due to long request time.
            if tab == "fully_churned":
                context[
                    "help_text"
                ] = f"""Locations that had orders in the previous 30 day period, but no orders in the last 30 day period
                    (old: {churn_date.strftime("%B %d, %Y")} - {cutoff_date.strftime("%B %d, %Y")},
                    new: {cutoff_date.strftime("%B %d, %Y")} - {datetime.date.today().strftime("%B %d, %Y")})."""
            else:
                context[
                    "help_text"
                ] = f"""Churning locations are those with a smaller revenue when compared to the previous
                    30 day period (old: {churn_date.strftime("%B %d, %Y")} - {cutoff_date.strftime("%B %d, %Y")},
                    new: {cutoff_date.strftime("%B %d, %Y")} - {datetime.date.today().strftime("%B %d, %Y")})."""
        else:
            user_addresses = get_location_objects(
                request,
                context["user"],
                context["user_group"],
                search_q=search_q,
                owner_id=account_owner_id,
            )

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
        context["page_current_link"] = (
            f"/customer/locations/?{query_params.urlencode()}"
        )
        if page_obj.has_previous():
            query_params["p"] = page_obj.previous_page_number()
            context["page_prev_link"] = (
                f"/customer/locations/?{query_params.urlencode()}"
            )
        if page_obj.has_next():
            query_params["p"] = page_obj.next_page_number()
            context["page_next_link"] = (
                f"/customer/locations/?{query_params.urlencode()}"
            )
        query_params["p"] = paginator.num_pages
        context["page_end_link"] = f"/customer/locations/?{query_params.urlencode()}"
        return render(
            request, "customer_dashboard/snippets/locations_table.html", context
        )

    query_params = request.GET.copy()
    if query_params.get("tab", None) is not None:
        context["locations_table_link"] = request.get_full_path()
    else:
        # Else load pending tab as default. customer_locations
        context["locations_table_link"] = (
            f"{reverse('customer_companies')}?{query_params.urlencode()}"
        )
    return render(request, "customer_dashboard/locations.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def location_detail(request, location_id):
    context = get_user_context(request)
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
        context["invoices"] = []
        invoices = Invoice.objects.filter(
            user_address_id=context["user_address"].id
        ).order_by("-due_date")
        if invoices.exists():
            context["invoices"] = invoices[:5]

    payment_methods = PaymentMethod.objects.filter(
        user_group_id=context["user_address"].user_group_id
    )
    # Order payment methods by newest first.
    payment_methods = payment_methods.order_by("-created_on")
    context["payment_methods"] = []
    for payment_method in payment_methods:
        if payment_method.id == context["user_address"].default_payment_method_id:
            setattr(payment_method, "is_default", True)
        context["payment_methods"].append(payment_method)

    if request.method == "POST":
        try:
            save_model = None
            form = UserAddressForm(
                request.POST, user=context["user"], auth_user=request.user
            )
            context["user_address_form"] = form
            if form.is_valid():
                if form.cleaned_data.get("name") != user_address.name:
                    user_address.name = form.cleaned_data.get("name")
                    save_model = user_address
                if form.cleaned_data.get("project_id") != user_address.project_id:
                    user_address.project_id = form.cleaned_data.get("project_id")
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
                if (
                    form.cleaned_data.get("tax_exempt_status")
                    != user_address.tax_exempt_status
                ):
                    user_address.tax_exempt_status = form.cleaned_data.get(
                        "tax_exempt_status"
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
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
            # messages.error(request, e.msg)
    else:
        context["form"] = AccessDetailsForm(
            initial={"access_details": user_address.access_details}
        )
        context["user_address_form"] = UserAddressForm(
            initial={
                "name": user_address.name,
                "project_id": user_address.project_id,
                "address_type": user_address.user_address_type_id,
                "street": user_address.street,
                "city": user_address.city,
                "state": user_address.state,
                "postal_code": user_address.postal_code,
                "is_archived": user_address.is_archived,
                "allow_saturday_delivery": user_address.allow_saturday_delivery,
                "allow_sunday_delivery": user_address.allow_sunday_delivery,
                "access_details": user_address.access_details,
                "tax_exempt_status": user_address.tax_exempt_status,
            },
            user=context["user"],
            auth_user=request.user,
        )

    # For any request type, get the current UserUserAddress objects.
    user_user_addresses = UserUserAddress.objects.filter(
        user_address_id=location_id
    ).select_related("user")

    user_user_location_normal = []
    user_user_location_normal_ids = []
    user_user_location_admin_users = []
    for user_user_address in user_user_addresses:
        if user_user_address.user.type == UserType.ADMIN:
            user_user_location_admin_users.append(user_user_address.user.id)
        else:
            user_user_location_normal.append(user_user_address)
            user_user_location_normal_ids.append(user_user_address.user.id)

    context["user_user_addresses"] = user_user_location_normal

    # Get the list of UserGroup Users that are not already associated with the SellerLocation.
    if user_address.user_group:
        context["non_associated_users"] = (
            User.objects.filter(
                user_group=user_address.user_group,
            )
            .exclude(
                id__in=user_user_location_normal_ids,
            )
            .exclude(
                type=UserType.ADMIN,
            )
        )

        # Get ADMIN users for this UserGroup.
        admin_users = User.objects.filter(
            user_group_id=user_address.user_group.id,
            type=UserType.ADMIN,
        )
        context["location_admins"] = []
        for user in admin_users:
            if user.id in user_user_location_admin_users:
                context["location_admins"].append({"user": user, "notify": True})
            else:
                context["location_admins"].append({"user": user, "notify": False})

    return render(request, "customer_dashboard/location_detail.html", context)


@login_required(login_url="/admin/login/")
def customer_location_user_add(request, user_address_id, user_id):
    user_address = UserAddress.objects.get(id=user_address_id)
    user = User.objects.get(id=user_id)

    # Throw error if user is not in the same seller group as the seller location.
    if user.user_group != user_address.user_group:
        return HttpResponse("Unauthorized", status=401)
    else:
        UserUserAddress.objects.create(
            user=user,
            user_address=user_address,
        )
        if request.headers.get("HX-Request"):
            return render(
                request,
                "customer_dashboard/snippets/user_user_address_row.html",
                {
                    "location_admin": {"user": user, "notify": True},
                    "user_address": user_address,
                },
            )
        else:
            return redirect(
                reverse(
                    "customer_location_detail",
                    kwargs={
                        "location_id": user_address_id,
                    },
                )
            )


@login_required(login_url="/admin/login/")
def customer_location_user_remove(request, user_address_id, user_id):
    user_address = UserAddress.objects.get(id=user_address_id)
    user = User.objects.get(id=user_id)

    # Throw error if user is not in the same seller group as the seller location.
    if user.user_group != user_address.user_group:
        return HttpResponse("Unauthorized", status=401)
    else:
        UserUserAddress.objects.filter(
            user=user,
            user_address=user_address,
        ).delete()
        if request.headers.get("HX-Request"):
            return render(
                request,
                "customer_dashboard/snippets/user_user_address_row.html",
                {
                    "location_admin": {"user": user, "notify": False},
                    "user_address": user_address,
                },
            )
        else:
            return redirect(
                reverse(
                    "customer_location_detail",
                    kwargs={
                        "location_id": user_address_id,
                    },
                )
            )


@login_required(login_url="/admin/login/")
@catch_errors()
def new_location(request):
    context = get_user_context(request)
    # If staff user and not impersonating, then warn that no customer is selected.
    if request.user.is_staff and not is_impersonating(request):
        messages.warning(
            request,
            f"No customer selected! Location would be added to your account [{request.user.email}].",
        )

    street = request.GET.get("street")
    city = request.GET.get("city")
    state = request.GET.get("state")
    postal_code = request.GET.get("zip")
    # This is a request from our website, so we want to redirect back to the bookings page on save.
    if street or city or state or postal_code:
        request.session["new_location_return_to"] = reverse("customer_home")

    # If there is a return_to url, then save it in the session.
    redirect_url = request.GET.get("return_to", None)
    if redirect_url:
        request.session["new_location_return_to"] = redirect_url

    # Only allow admin to create new users.
    if context["user"].type != UserType.ADMIN:
        messages.error(request, "Only admins can create new locations.")
        return HttpResponseRedirect(reverse("customer_locations"))

    if request.method == "POST":
        try:
            save_model = None
            if "user_address_submit" in request.POST:
                form = UserAddressForm(
                    request.POST, user=context["user"], auth_user=request.user
                )
                context["user_address_form"] = form
                if form.is_valid():
                    name = form.cleaned_data.get("name")
                    project_id = form.cleaned_data.get("project_id")
                    address_type = form.cleaned_data.get("address_type")
                    street = form.cleaned_data.get("street")
                    city = form.cleaned_data.get("city")
                    state = form.cleaned_data.get("state")
                    postal_code = form.cleaned_data.get("postal_code")
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
                        project_id=project_id,
                        street=street,
                        city=city,
                        state=state,
                        country="US",
                        postal_code=postal_code,
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
                # If user is not admin, then add access to the location.
                if context["user"].type != UserType.ADMIN:
                    UserUserAddress.objects.get_or_create(
                        user=context["user"],
                        user_address=save_model,
                    )
                messages.success(request, "Successfully saved!")
                redirect_url = request.session.get(
                    "new_location_return_to",
                    reverse(
                        "customer_location_detail",
                        kwargs={
                            "location_id": save_model.id,
                        },
                    ),
                )
                if "new_location_return_to" in request.session:
                    del request.session["new_location_return_to"]
                return HttpResponseRedirect(redirect_url)
            else:
                messages.info(request, "No changes detected.")
                return HttpResponseRedirect(reverse("customer_locations"))

        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
            # messages.error(request, "Error saving, please contact us if this continues.")
            # messages.error(request, e.msg)
    else:
        initial_data = {}
        if street:
            initial_data["street"] = street
        if city:
            initial_data["city"] = city
        if state:
            initial_data["state"] = state
        if postal_code:
            initial_data["postal_code"] = postal_code

        context["user_address_form"] = UserAddressForm(
            initial=initial_data, user=context["user"], auth_user=request.user
        )

    return render(request, "customer_dashboard/location_new_edit.html", context)


@login_required(login_url="/admin/login/")
def user_associated_locations(request, user_id):
    context = {}
    context["associated_locations"] = UserAddress.objects.filter(
        user_id=user_id
    ).count()
    # Assume htmx request
    # if request.headers.get("HX-Request"):
    return render(
        request,
        "customer_dashboard/snippets/user_associated_locations_count.html",
        context,
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def users(request):
    context = get_user_context(request)
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    user_id = request.GET.get("user_id", None)
    date = request.GET.get("date", None)
    search_q = request.GET.get("q", None)
    # location_id = request.GET.get("location_id", None)
    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        tab = request.GET.get("tab", None)

        account_filter = request.GET.get("account_filter", None)
        account_owner_id = None
        if request.user.is_staff and account_filter == "my_accounts":
            account_owner_id = request.user.id

        context["tab"] = tab
        query_params = request.GET.copy()

        if request.user.is_staff and tab == "new":
            users = UserUtils.get_new(search_q=search_q, owner_id=account_owner_id)
            context["help_text"] = "New users created in the last 30 days."
        elif request.user.is_staff and tab == "loggedin":
            users = UserUtils.get_loggedin(search_q=search_q, owner_id=account_owner_id)
            context["help_text"] = (
                "Get all users who have logged in, in the last 30 days."
            )
        elif request.user.is_staff and tab == "active":
            users = UserUtils.get_active(search_q=search_q, owner_id=account_owner_id)
            context["help_text"] = "Active users with orders in the last 30 days."
            pagination_limit = 100  # Create large limit due to long request time
        elif request.user.is_staff and (tab == "churned" or tab == "fully_churned"):
            cutoff_date = datetime.date.today() - datetime.timedelta(days=30)
            churn_date = datetime.date.today() - datetime.timedelta(days=60)
            users = UserUtils.get_churning(
                search_q=search_q,
                tab=tab,
                old_date=churn_date,
                new_date=cutoff_date,
                owner_id=account_owner_id,
            )
            pagination_limit = 200  # Create large limit due to long request time.
            if tab == "fully_churned":
                context[
                    "help_text"
                ] = f"""Users that had orders in the previous 30 day period, but no orders in the last 30 day period
                    (old: {churn_date.strftime("%B %d, %Y")} - {cutoff_date.strftime("%B %d, %Y")},
                    new: {cutoff_date.strftime("%B %d, %Y")} - {datetime.date.today().strftime("%B %d, %Y")})."""
            else:
                context[
                    "help_text"
                ] = f"""Churning users are those with a smaller revenue when compared to the previous
                    30 day period (old: {churn_date.strftime("%B %d, %Y")} - {cutoff_date.strftime("%B %d, %Y")},
                    new: {cutoff_date.strftime("%B %d, %Y")} - {datetime.date.today().strftime("%B %d, %Y")})."""
        else:
            users = get_user_group_user_objects(
                request, context["user"], context["user_group"], search_q=search_q
            )
            if date:
                users = users.filter(date_joined__date=date)
            if account_owner_id:
                users = users.filter(user_group__account_owner_id=account_owner_id)
            users = users.order_by("-date_joined")

        paginator = Paginator(users, pagination_limit)
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
        return render(request, "customer_dashboard/snippets/users_table.html", context)

    query_params = request.GET.copy()
    if query_params.get("tab", None) is not None:
        context["users_table_link"] = request.get_full_path()
    else:
        # Else load pending tab as default
        context["users_table_link"] = (
            f"{reverse('customer_users')}?{query_params.urlencode()}"
        )

    return render(request, "customer_dashboard/users.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def user_detail(request, user_id):
    context = {}
    # This is an HTMX request, so respond with html snippet
    # if request.headers.get("HX-Request"):
    user = User.objects.get(id=user_id)
    context["user"] = user
    user_group = get_user_group(request)
    context["user_group"] = user_group
    context["theme"] = get_theme(user_group)
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
        form = UserForm(POST_COPY, request.FILES, instance=user, auth_user=request.user)
        context["form"] = form
        if form.is_valid():
            if form.has_changed():
                form.save()
                context["user"] = user
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")
            # Reload the form with the updated data (for some reason it doesn't update the form with the POST data).
            form = UserForm(instance=user, auth_user=request.user)
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
        form = UserForm(instance=user, auth_user=request.user)
        context["form"] = form

    return render(request, "customer_dashboard/user_detail.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def user_reset_password(request, user_id):
    # context = get_user_context(request)
    if request.method == "POST":
        try:
            user = User.objects.get(id=user_id)
            if not user.redirect_url:
                user.redirect_url = "/customer/"
                user.save()
            user.reset_password()
        except User.DoesNotExist:
            return HttpResponse("User not found", status=404)

    return HttpResponse(status=204)


@login_required(login_url="/admin/login/")
@catch_errors()
def user_update_email(request, user_id):
    # context = get_user_context(request)

    context = {}
    context["help_msg"] = ""
    context["css_class"] = "form-valid"
    context["step1"] = True
    try:
        context["user"] = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return HttpResponseRedirect(reverse("customer_users"))
    if request.user.id != context["user"].id:
        messages.error(request, "You do not have permission to update this email.")
        return HttpResponseRedirect(reverse("customer_profile"))

    if request.method == "POST":
        # if "submit_email" in request.POST:
        new_email = request.POST.get("email")
        code = request.POST.get("code")
        try:
            if new_email:
                new_email = new_email.casefold()
                validate_email(new_email)
                if User.objects.filter(email=new_email).exists():
                    messages.error(request, "User with that email already exists.")
                    context["error"] = "User with that email already exists."
                    context["css_class"] = "form-error"
                else:
                    otp = get_otp()
                    request.session["otp"] = otp
                    request.session["new_email"] = new_email
                    request.session["otp_expiration"] = time.time() + 600  # 10 minutes
                    context["user"].send_otp_email(new_email, otp)
                    context["help_msg"] = (
                        f"Successfully sent verification code to {new_email}!"
                    )
                    messages.success(
                        request,
                        f"Successfully sent verification code to {new_email}! Please check your email for the code!",
                    )
                    context["step1"] = False
            elif code:
                context["step1"] = False
                new_email = request.session.get("new_email")
                if not new_email:
                    raise ValidationError("Please retry.")
                if (
                    request.session.get("otp") == code
                    and request.session.get("otp_expiration") > time.time()
                ):
                    auth0.update_user_email(
                        context["user"].user_id, new_email, verify_email=False
                    )
                    context["user"].username = new_email
                    context["user"].email = new_email
                    context["user"].save()
                    messages.success(request, "Successfully updated email!")
                    context["step1"] = True
                    del request.session["otp"]
                    del request.session["new_email"]
                    del request.session["otp_expiration"]
                    return HttpResponseRedirect(reverse("customer_profile"))
                else:
                    messages.error(request, "Invalid or expired code.")
                    context["error"] = "Invalid or expired code."
                    context["css_class"] = "form-error"
        except ValidationError as e:
            messages.error(request, f"{e}")
            context["error"] = f"{e}"
            context["css_class"] = "form-error"
        except Exception as e:
            logger.error(
                f"user_update_email: Error updating email: [{user_id}]-[{e}]",
                exc_info=e,
            )
            messages.error(
                request,
                f"Error updating email. Please contact us if this continues. [{e}]",
            )
            context["error"] = f"Error updating email: {e}"
            context["css_class"] = "form-error"
    else:
        pass

    return render(request, "customer_dashboard/user_update_email.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def new_user(request):
    context = get_user_context(request)
    redirect_url = request.GET.get("return_to")

    # Only allow admin to create new users.
    if context["user"].type != UserType.ADMIN:
        messages.error(request, "Only admins can create new users.")

        if redirect_url:
            return HttpResponseRedirect(redirect_url)
        else:
            return HttpResponseRedirect(reverse("customer_users"))

    if redirect_url:
        request.session["new_user_return_to"] = redirect_url

    if request.method == "POST":
        try:
            save_model = None
            POST_COPY = request.POST.copy()
            # POST_COPY["email"] = user.email
            form = UserInviteForm(POST_COPY, request.FILES, auth_user=context["user"])
            context["form"] = form
            show_default_message = True
            # Default to the current user's UserGroup.
            user_group_id = context["user"].user_group_id
            if not context["user_group"] and request.user.is_staff:
                usergroup_id = request.POST.get("usergroupId")
                if usergroup_id:
                    user_group = UserGroup.objects.get(id=usergroup_id)
                    user_group_id = user_group.id
            if form.is_valid():
                first_name = form.cleaned_data.get("first_name")
                last_name = form.cleaned_data.get("last_name")
                email = form.cleaned_data.get("email").casefold()
                phone = form.cleaned_data.get("phone")
                user_type = form.cleaned_data.get("type")
                # Check if email is already in use.
                other_user = User.objects.filter(email__iexact=email).first()
                if other_user:
                    if other_user.user_group:
                        raise UserAlreadyExistsError()
                    else:
                        # Add the user to the UserGroup.
                        user_group = UserGroup.objects.get(id=user_group_id)
                        user_group.invite_user(other_user)
                        messages.success(request, f"Successfully invited {email}!")
                        show_default_message = False
                else:
                    if request.user.is_staff:
                        # directly create the user
                        user = User(
                            user_group_id=user_group_id,
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            phone=phone,
                            source=User.Source.SALES,
                            type=user_type,
                            redirect_url="/customer/",
                        )
                        save_model = user
                        logger.debug("Directly created user.")
                    elif user_group_id:
                        user_invite = UserGroupAdminApprovalUserInvite(
                            user_group_id=user_group_id,
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            phone=phone,
                            type=user_type,
                            redirect_url="/customer/",
                        )
                        save_model = user_invite
                    else:
                        raise ValueError(
                            f"User:[{context['user'].id}]-UserGroup:[{user_group_id}]-invite attempt:[{email}]"
                        )
            else:
                raise InvalidFormError(form, "Invalid UserInviteForm")
            if save_model:
                save_model.save()
                messages.success(request, "Successfully saved!")
            elif show_default_message:
                messages.info(request, "No changes detected.")

            redirect_url = request.session.get(
                "new_user_return_to",
                reverse("customer_users"),
            )
            if "new_user_return_to" in request.session:
                del request.session["new_user_return_to"]
            return HttpResponseRedirect(redirect_url)
        except UserAlreadyExistsError:
            messages.error(request, "User with that email already exists.")
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            for field in e.form.errors:
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
        except IntegrityError as e:
            if "unique constraint" in str(e):
                messages.error(request, "User with that email already exists.")
            else:
                messages.error(
                    request, "Error saving, please contact us if this continues."
                )
                messages.error(request, f"Database IntegrityError:[{e}]")
        except Exception as e:
            messages.error(
                request, "Error saving, please contact us if this continues."
            )
            messages.error(request, e)
    else:
        context["form"] = UserInviteForm(auth_user=context["user"])

    return render(request, "customer_dashboard/user_new_edit.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def invoices(request):
    context = get_user_context(request)
    pagination_limit = 100
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    date = request.GET.get("date", None)
    location_id = request.GET.get("location_id", None)
    query_params = request.GET.copy()
    search_q = request.GET.get("q", None)
    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        tab = request.GET.get("tab", None)
        context["tab"] = tab

        invoices = get_invoice_objects(request, context["user"], context["user_group"])
        if location_id:
            invoices = invoices.filter(user_address_id=location_id)
        if date:
            invoices = invoices.filter(due_date__date=date)
        if search_q:
            invoices = invoices.filter(
                Q(number__icontains=search_q)
                | Q(invoice_id__icontains=search_q)
                | Q(user_address__name__icontains=search_q)
                | Q(user_address__project_id__icontains=search_q)
                | Q(user_address__street__icontains=search_q)
                | Q(user_address__city__icontains=search_q)
                | Q(user_address__state__icontains=search_q)
                | Q(user_address__postal_code__icontains=search_q)
                | Q(user_address__project_id__icontains=search_q)
            )
        invoices = invoices.order_by(F("due_date").desc(nulls_last=True))
        today = timezone.now().today().date()
        if tab:
            if tab == "past_due":
                # Get all invoices that are past due.
                invoices = invoices.filter(
                    Q(due_date__date__lt=today)
                    & Q(status=Invoice.Status.OPEN)
                    & Q(amount_remaining__gt=0)
                )
            else:
                if tab == "paid":
                    invoices = invoices.filter(
                        Q(status=Invoice.Status.PAID) | Q(status=Invoice.Status.VOID)
                    )
                else:
                    invoices = invoices.filter(status=tab)
        else:
            # Get all invoices. Calculate the total paid, past due, and total open invoices.
            context["total_paid"] = 0
            context["past_due"] = 0
            context["total_open"] = 0
            for invoice in invoices:
                amount_paid = invoice.amount_paid
                amount_remaining = invoice.amount_remaining
                # Manually setting Stripe invoice to paid does not update the amount_paid, so assume it is paid.
                if (
                    invoice.status == Invoice.Status.PAID
                    or invoice.status == Invoice.Status.VOID
                ):
                    amount_paid = invoice.total
                    amount_remaining = 0
                context["total_paid"] += amount_paid
                context["total_open"] += amount_remaining
                if invoice.due_date and invoice.due_date.date() < today:
                    context["past_due"] += amount_remaining

        paginator = Paginator(invoices, pagination_limit)
        page_obj = paginator.get_page(page_number)
        context["page_obj"] = page_obj

        if page_number is None:
            page_number = 1
        else:
            page_number = int(page_number)

        query_params["p"] = 1
        context["page_start_link"] = (
            f"{reverse('customer_invoices')}?{query_params.urlencode()}"
        )
        query_params["p"] = page_number
        context["page_current_link"] = (
            f"{reverse('customer_invoices')}?{query_params.urlencode()}"
        )
        if page_obj.has_previous():
            query_params["p"] = page_obj.previous_page_number()
            context["page_prev_link"] = (
                f"{reverse('customer_invoices')}?{query_params.urlencode()}"
            )
        if page_obj.has_next():
            query_params["p"] = page_obj.next_page_number()
            context["page_next_link"] = (
                f"{reverse('customer_invoices')}?{query_params.urlencode()}"
            )
        query_params["p"] = paginator.num_pages
        context["page_end_link"] = (
            f"{reverse('customer_invoices')}?{query_params.urlencode()}"
        )
        return render(
            request, "customer_dashboard/snippets/invoices_table.html", context
        )

    if query_params.get("tab", None) is not None:
        context["data_link"] = request.get_full_path()
    else:
        # Else load pending tab as default
        context["data_link"] = (
            f"{reverse('customer_invoices')}?{query_params.urlencode()}"
        )
    return render(request, "customer_dashboard/invoices.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def invoice_detail(request, invoice_id):
    context = get_user_context(request)
    context["invoice"] = Invoice.objects.get(id=invoice_id)
    context["is_checkout"] = True
    if context["user_group"]:
        payment_methods = PaymentMethod.objects.filter(
            user_group_id=context["user_group"].id
        )
    else:
        # Get account from location. This is helpful for impersonations.
        if context["invoice"].user_address.user_group:
            payment_methods = PaymentMethod.objects.filter(
                user_group_id=context["invoice"].user_address.user_group.id
            )
            context["user_group"] = context["invoice"].user_address.user_group
        else:
            payment_methods = PaymentMethod.objects.filter(user_id=context["user"].id)
    # Order payment methods by newest first.
    context["payment_methods"] = payment_methods.order_by("-created_on")

    if request.method == "POST":
        if "check_sent_at_submit" in request.POST:
            check_sent_at = request.POST.get("check_sent_at")
            if check_sent_at:
                try:
                    # Parse the date string into a datetime object
                    check_sent_at = datetime.datetime.strptime(
                        check_sent_at, "%Y-%m-%d"
                    )
                    # Make the datetime object timezone-aware
                    check_sent_at = timezone.make_aware(
                        check_sent_at, timezone.get_current_timezone()
                    )
                    # Do not allow a date more than 2 days in the future
                    cutoff_date = datetime.date.today() + datetime.timedelta(days=2)
                    if check_sent_at.date() > cutoff_date:
                        # Set the error message to may not select a date after 2 days in the future
                        messages.error(
                            request, f"May not select a date after {cutoff_date}."
                        )
                        return HttpResponseRedirect(
                            reverse(
                                "customer_invoice_detail",
                                kwargs={"invoice_id": context["invoice"].id},
                            )
                        )
                    # Assign the date to the invoice and save
                    context["invoice"].check_sent_at = check_sent_at.date()
                    context["invoice"].save()
                except ValueError:
                    # Handle the case where the date string is not in the expected format
                    messages.error(request, "Invalid date format.")
            else:
                context["invoice"].check_sent_at = None
                context["invoice"].save()
        else:
            payment_method_id = request.POST.get("payment_method")
            if payment_method_id:
                payment_method = PaymentMethod.objects.get(id=payment_method_id)
                context["invoice"].pay_invoice(payment_method)
                messages.success(request, "Successfully paid!")
            else:
                messages.error(request, "Invalid payment method.")

    return render(request, "customer_dashboard/invoice_detail.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def companies(request):
    context = get_user_context(request)
    context["help_text"] = (
        "Companies [ list of comanies where UserGroup.Seller == NULL ]"
    )
    if not request.user.is_staff:
        return HttpResponseRedirect(reverse("customer_home"))
    pagination_limit = 25
    page_number = 1
    if request.GET.get("p", None) is not None:
        page_number = request.GET.get("p")
    search_q = request.GET.get("q", None)
    # location_id = request.GET.get("location_id", None)
    # This is an HTMX request, so respond with html snippet
    if request.headers.get("HX-Request"):
        tab = request.GET.get("tab", None)
        account_filter = request.GET.get("account_filter")
        account_owner_id = None
        if account_filter == "my_accounts":
            account_owner_id = request.user.id
        missing_owner = account_filter == "missing_owner"

        # TODO: If impersonating a company, then only show that company.
        context["tab"] = tab
        query_params = request.GET.copy()

        if tab == "new":
            user_groups = UserGroupUtils.get_new(
                search_q=search_q,
                owner_id=account_owner_id,
                missing_owner=missing_owner,
            )
            context["help_text"] = "New Companies created in the last 30 days."
        elif tab == "active":
            user_groups = UserGroupUtils.get_active(
                search_q=search_q,
                owner_id=account_owner_id,
                missing_owner=missing_owner,
            )
            context["help_text"] = "Active Companies with orders in the last 30 days."
            pagination_limit = 100
        elif tab == "churned" or tab == "fully_churned":
            cutoff_date = datetime.date.today() - datetime.timedelta(days=30)
            churn_date = datetime.date.today() - datetime.timedelta(days=60)
            user_groups = UserGroupUtils.get_churning(
                search_q=search_q,
                tab=tab,
                old_date=churn_date,
                new_date=cutoff_date,
                owner_id=account_owner_id,
                missing_owner=missing_owner,
            )
            pagination_limit = len(user_groups) or 1
            if tab == "fully_churned":
                context[
                    "help_text"
                ] = f"""Companies that had orders in the previous 30 day period, but no orders in the last 30 day period
                    (old: {churn_date.strftime("%B %d, %Y")} - {cutoff_date.strftime("%B %d, %Y")},
                    new: {cutoff_date.strftime("%B %d, %Y")} - {datetime.date.today().strftime("%B %d, %Y")})."""
            else:
                context[
                    "help_text"
                ] = f"""Churning Companies are those with a smaller revenue when compared to the previous
                    30 day period (old: {churn_date.strftime("%B %d, %Y")} - {cutoff_date.strftime("%B %d, %Y")},
                    new: {cutoff_date.strftime("%B %d, %Y")} - {datetime.date.today().strftime("%B %d, %Y")})."""
        else:
            user_groups = UserGroup.objects.filter(seller__isnull=True)
            if account_owner_id:
                user_groups = user_groups.filter(account_owner_id=account_owner_id)
            elif missing_owner:
                user_groups = user_groups.filter(account_owner_id__isnull=True)
            if search_q:
                user_groups = user_groups.filter(name__icontains=search_q)
            user_groups = user_groups.order_by("name")

        paginator = Paginator(user_groups, pagination_limit)
        page_obj = paginator.get_page(page_number)
        context["page_obj"] = page_obj

        if page_number is None:
            page_number = 1
        else:
            page_number = int(page_number)

        query_params["p"] = 1
        context["page_start_link"] = f"/customer/companies/?{query_params.urlencode()}"
        query_params["p"] = page_number
        context["page_current_link"] = (
            f"/customer/companies/?{query_params.urlencode()}"
        )
        if page_obj.has_previous():
            query_params["p"] = page_obj.previous_page_number()
            context["page_prev_link"] = (
                f"/customer/companies/?{query_params.urlencode()}"
            )
        if page_obj.has_next():
            query_params["p"] = page_obj.next_page_number()
            context["page_next_link"] = (
                f"/customer/companies/?{query_params.urlencode()}"
            )
        query_params["p"] = paginator.num_pages
        context["page_end_link"] = f"/customer/companies/?{query_params.urlencode()}"
        return render(
            request, "customer_dashboard/snippets/companies_table.html", context
        )

    query_params = request.GET.copy()
    if query_params.get("tab", None) is not None:
        context["companies_table_link"] = request.get_full_path()
    else:
        # Else load pending tab as default
        context["companies_table_link"] = (
            f"{reverse('customer_companies')}?{query_params.urlencode()}"
        )
    return render(request, "customer_dashboard/companies.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def company_detail(request, user_group_id=None):
    context = get_user_context(request, add_user_group=False)
    if not user_group_id:
        if request.user.type != UserType.ADMIN:
            return HttpResponseRedirect(reverse("customer_home"))
        user_group = get_user_group(request)
        if not user_group:
            if hasattr(request.user, "user_group") and request.user.user_group:
                user_group = request.user.user_group
                messages.warning(
                    request,
                    f"No customer selected! Using current staff user group [{request.user.user_group}].",
                )
            else:
                # Get first available UserGroup.
                user_group = UserGroup.objects.all().first()
                messages.warning(
                    request,
                    f"No customer selected! Using first user group found: [{user_group.name}].",
                )
    else:
        # Only allow admin to save company settings.
        if not request.user.is_staff and context["user"].type != UserType.ADMIN:
            messages.error(request, "Only admins can edit Company Settings.")
            return HttpResponseRedirect(reverse("customer_home"))
        user_group = UserGroup.objects.filter(id=user_group_id)
        user_group = user_group.prefetch_related("users", "user_addresses")
        user_group = user_group.first()
    context["user_group"] = user_group
    context["theme"] = get_theme(user_group)
    context["user"] = user_group.users.filter(type=UserType.ADMIN).first()
    user_group_id = None
    if context["user_group"]:
        user_group_id = context["user_group"].id
    else:
        user_group_id = context["user"].user_group_id
    payment_methods = PaymentMethod.objects.filter(user_group_id=user_group_id)
    # Order payment methods by newest first.
    context["payment_methods"] = payment_methods.order_by("-created_on")
    context["credit_application"] = (
        context["user_group"].credit_applications.order_by("-created_on").first()
    )

    # Fill forms with initial data
    context["form"] = UserGroupForm(
        instance=user_group,
        user=context["user"],
        auth_user=request.user,
    )
    context["paymentDetailsForm"] = paymentDetailsForm(
        instance=user_group,
        user=context["user"],
        auth_user=request.user,
    )

    context["branding_formset"] = BrandingFormSet(instance=user_group)

    if context.get("user"):
        context["types"] = context["user"].get_allowed_user_types()

    if request.method == "POST":
        # Update branding settings.
        if "branding_form" in request.POST:
            branding_formset = BrandingFormSet(
                request.POST, request.FILES, instance=user_group
            )
            context["branding_formset"] = branding_formset

            if branding_formset.is_valid():
                # Check if any changes to form were made
                if branding_formset.has_changed():
                    branding_formset.save()
                    # Update theme to render new branding
                    context.update(
                        {
                            "branding_formset": BrandingFormSet(instance=user_group),
                            "user_group": user_group,
                            "theme": get_theme(user_group),
                        }
                    )
                    messages.success(request, "Successfully saved!")
                else:
                    messages.info(request, "No changes detected.")

            return render(request, "customer_dashboard/company_detail.html", context)

        # Update payment details.
        if "payment_details_button" in request.POST:
            payment_details_form = paymentDetailsForm(
                request.POST,
                request.FILES,
                instance=user_group,
                user=context["user"],
                auth_user=request.user,
            )
            context["paymentDetailsForm"] = payment_details_form

            if payment_details_form.is_valid():
                # Check if any changes to form were made
                if payment_details_form.has_changed():
                    payment_details_form.save()
                    messages.success(request, "Successfully saved!")
                else:
                    messages.info(request, "No changes detected.")

            return render(request, "customer_dashboard/company_detail.html", context)

        # Update form
        form = UserGroupForm(
            request.POST,
            request.FILES,
            instance=user_group,
            user=context["user"],
            auth_user=request.user,
        )
        context["form"] = form
        if form.is_valid():
            if form.has_changed():
                form.save()
                context["user_group"] = user_group
                messages.success(request, "Successfully saved!")
            else:
                messages.info(request, "No changes detected.")

            # Reload the form with the updated data
            form = UserGroupForm(
                instance=user_group,
                user=context["user"],
                auth_user=request.user,
            )
            context["form"] = form
            # return HttpResponse("", status=200)
            # This is an HTMX request, so respond with html snippet
            # if request.headers.get("HX-Request"):
            return render(request, "customer_dashboard/company_detail.html", context)
        else:
            # This will let bootstrap know to highlight the fields with errors.
            for field in form.errors:
                if field == "__all__":
                    continue
                form[field].field.widget.attrs["class"] += " is-invalid"
            messages.error(
                request, "There was an error in the submission, check form below."
            )

    return render(request, "customer_dashboard/company_detail.html", context)


@login_required(login_url="/admin/login/")
def user_email_check(request):
    context = {}
    context["user"] = get_user(request)
    context["help_msg"] = ""
    context["css_class"] = "form-valid"
    if request.method == "POST":
        context["email"] = request.POST.get("email")
        context["phone"] = request.POST.get("phone")
        context["first_name"] = request.POST.get("first_name")
        context["last_name"] = request.POST.get("last_name")
        context["apollo_id"] = request.POST.get("apollo_id")
        context["type"] = request.POST.get("type")
        if context["type"]:
            context["types"] = context["user"].get_allowed_user_types()
    else:
        return HttpResponse("Invalid request method.", status=400)
    if context["email"]:
        try:
            validate_email(context["email"])
            if User.objects.filter(email=context["email"].casefold()).exists():
                user = User.objects.get(email=context["email"].casefold())
                if user.user_group:
                    context["error"] = (
                        f"User [{context['email']}] already exists in UserGroup [{user.user_group.name}]."
                    )
                    context["css_class"] = "form-error"
                else:
                    context["help_msg"] = "Found existing user with that email."
                    context["email"] = user.email
                    context["phone"] = user.phone
                    context["first_name"] = user.first_name
                    context["last_name"] = user.last_name
                    context["apollo_id"] = user.apollo_id
                    context["type"] = user.type
        except ValidationError as e:
            context["error"] = f"{e}"
            context["css_class"] = "form-error"

    # Assume htmx request
    # if request.headers.get("HX-Request"):
    return render(
        request,
        "customer_dashboard/snippets/email_check.html",
        context,
    )


@login_required(login_url="/admin/login/")
@catch_errors()
def new_company(request):
    context = get_user_context(request, add_user_group=False)
    if not request.user.is_staff:
        return HttpResponseRedirect(reverse("customer_home"))
    context["user_group"] = None
    context["help_msg"] = "Enter new or existing user email."
    if request.method == "POST":
        try:
            form = UserGroupNewForm(
                request.POST,
                request.FILES,
                user=context["user"],
                auth_user=request.user,
            )
            POST_COPY = request.POST.copy()
            if request.POST.get("type"):
                context["type"] = request.POST.get("type")
            else:
                POST_COPY["type"] = UserType.ADMIN
            user_form = UserForm(POST_COPY, request.FILES)
            user_form.fields["email"].disabled = False
            user_form.fields["source"].required = False
            context["user_form"] = user_form
            context["email"] = request.POST.get("email")
            context["phone"] = request.POST.get("phone")
            context["first_name"] = request.POST.get("first_name")
            context["last_name"] = request.POST.get("last_name")
            context["form"] = form

            if form.is_valid():
                # Create New UserGroup
                user_group = UserGroup(
                    name=form.cleaned_data.get("name"),
                )
                email = request.POST.get("email").casefold()

                if email and User.objects.filter(email__iexact=email).exists():
                    # Update Existing User
                    user = User.objects.get(email__iexact=email)
                    if user.user_group:
                        messages.error(
                            request,
                            f"User with email [{email}] already exists in UserGroup [{user.user_group.name}].",
                        )
                    else:
                        context["user_group"] = user_group
                        user_group.save()  # Only save if User will be saved.
                        user.user_group = user_group
                        user.save()
                        messages.success(request, "Successfully saved!")
                        return HttpResponseRedirect(
                            reverse(
                                "customer_company_detail",
                                kwargs={
                                    "user_group_id": user_group.id,
                                },
                            )
                        )
                else:
                    # Create New User
                    if user_form.is_valid():
                        context["user_group"] = user_group
                        user_group.save()  # Only save if User will be saved.
                        user = User(
                            first_name=user_form.cleaned_data.get("first_name"),
                            last_name=user_form.cleaned_data.get("last_name"),
                            email=email,
                            phone=user_form.cleaned_data.get("phone"),
                            source=User.Source.SALES,
                            type=user_form.cleaned_data.get("type"),
                            user_group=user_group,
                        )
                        user.save()
                        messages.success(request, "Successfully saved!")
                        return redirect(
                            reverse(
                                "customer_company_detail",
                                kwargs={
                                    "user_group_id": user_group.id,
                                },
                            )
                        )
                    else:
                        messages.error(
                            request,
                            "Error saving, please contact us if this continues.",
                        )
            else:
                # This will let bootstrap know to highlight the fields with errors.
                for field in form.errors:
                    form[field].field.widget.attrs["class"] += " is-invalid"
                messages.error(
                    request, "Error saving, please contact us if this continues."
                )
        except Exception as e:
            messages.error(
                request, f"Error saving, please contact us if this continues. [{e}]"
            )
            logger.error(f"new_company: [{e}]", exc_info=e)
    else:
        context["form"] = UserGroupNewForm(user=context["user"], auth_user=request.user)

    return render(request, "customer_dashboard/company_new.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def company_new_user(request, user_group_id):
    context = get_user_context(request, add_user_group=False)
    user_group = UserGroup.objects.get(id=user_group_id)
    context["user_group"] = user_group
    context["theme"] = get_theme(user_group)

    # Only allow admin to create new users.
    if context["user"].type != UserType.ADMIN:
        messages.error(request, "Only admins can create new users.")
        return HttpResponseRedirect(request.get_full_path())

    if request.method == "POST":
        try:
            save_model = None
            POST_COPY = request.POST.copy()
            # POST_COPY["email"] = user.email
            form = UserInviteForm(POST_COPY, request.FILES, auth_user=context["user"])
            context["form"] = form
            if form.is_valid():
                context["first_name"] = form.cleaned_data.get("first_name")
                context["last_name"] = form.cleaned_data.get("last_name")
                context["email"] = form.cleaned_data.get("email")
                context["phone"] = form.cleaned_data.get("phone")
                context["type"] = form.cleaned_data.get("type")
                context["types"] = context["user"].get_allowed_user_types()
                # Check if email is already in use.
                if (
                    context["email"]
                    and User.objects.filter(email=context["email"].casefold()).exists()
                ):
                    user = User.objects.get(email=context["email"].casefold())
                    if user.user_group:
                        raise UserAlreadyExistsError()
                    else:
                        user.user_group = context["user_group"]
                        save_model = user
                else:
                    user_invite = UserGroupAdminApprovalUserInvite(
                        user_group_id=context["user_group"].id,
                        first_name=context["first_name"],
                        last_name=context["last_name"],
                        email=context["email"],
                        phone=context["phone"],
                        type=context["type"],
                    )
                    save_model = user_invite
            else:
                raise InvalidFormError(form, "Invalid UserInviteForm")
            if save_model:
                save_model.save()
                context["form_msg"] = "Successfully saved!"
                context["first_name"] = context["last_name"] = context[
                    "email"
                ] = context["type"] = context["phone"] = ""
        except UserAlreadyExistsError:
            context["form_error"] = "User with that email already exists."
        except InvalidFormError as e:
            # This will let bootstrap know to highlight the fields with errors.
            context["form_error"] = ""
            for field in e.form.errors:
                if e.form.fields[field].widget.attrs.get("class", None) is None:
                    e.form.fields[field].widget.attrs["class"] = "is-invalid"
                else:
                    e.form.fields[field].widget.attrs["class"] += " is-invalid"
                context["form_error"] += f"{field}: {e.form[field].errors}"
        except Exception as e:
            context["form_error"] = (
                f"Error saving, please contact us if this continues: [{e}]."
            )
            messages.error(request, e)
    else:
        context["types"] = context["user"].get_allowed_user_types()

    return render(request, "customer_dashboard/snippets/company_new_user.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def reports(request):
    from billing.scheduled_jobs.consolidated_account_summary import get_account_summary
    from billing.scheduled_jobs.consolidated_account_past_due import (
        get_account_past_due,
    )
    from common.utils import customerio

    context = get_user_context(request)
    if not request.user.is_staff or not context["user_group"]:
        return HttpResponseRedirect(reverse("customer_home"))

    tab = request.GET.get("tab", None)
    if tab is None:
        tab = request.POST.get("tab", None)
    context["tab"] = tab
    template = "customer_dashboard/snippets/account_summary_report.html"
    if tab == "past_due":
        template = "customer_dashboard/snippets/account_past_due_report.html"
        context["report_results"] = get_account_past_due(context["user_group"])
    else:
        context["report_results"] = get_account_summary(context["user_group"])
    if request.headers.get("HX-Request"):
        if request.method == "POST":
            customerid_id = 7
            if tab == "past_due":
                customerid_id = 8
                subject = f"{context['user_group'].name}'s Past Due Notice From Downstream Marketplace"
            else:
                subject = f"{context['user_group'].name}'s Account Summary With Downstream Marketplace"
            customerio.send_email(
                ["mwickey@trydownstream.com"],
                context["report_results"],
                subject,
                customerid_id,
            )
            return HttpResponse("", status=200)
        else:
            return render(request, template, context)
    return render(request, "customer_dashboard/reports.html", context)


@login_required(login_url="/admin/login/")
@catch_errors()
def reviews(request):
    """
    Handles the reviews view for the customer dashboard.

    This view is responsible for displaying reviews or aggregating
    review data based on the selected tab (users or sellers).

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The HTTP response object with the rendered template.
    """
    if not request.user.is_staff:
        return HttpResponseRedirect(reverse("customer_home"))

    context = get_user_context(request)
    pagination_limit = 25
    page_number = 1

    if request.GET.get("p"):
        page_number = request.GET.get("p")

    if request.headers.get("HX-Request"):
        # This is an HTMX request, so respond with html snippet
        tab = request.GET.get("tab", None)
        context["tab"] = tab
        query_params = request.GET.copy()

        # Build Query
        if tab == "users":
            context["help_text"] = "Reviews made by Users"
            reviews = (
                User.objects.values(
                    "id", "first_name", "last_name", "photo_url", "email"
                )
                .annotate(
                    rating=Sum(
                        Case(
                            When(ordergroup__orders__review__rating=True, then=1),
                            default=0,
                            output_field=IntegerField(),
                        )
                    ),
                    negative_rating=Sum(
                        Case(
                            When(ordergroup__orders__review__rating=False, then=1),
                            default=0,
                            output_field=IntegerField(),
                        )
                    ),
                    # Round averages to 1 decimal place
                    professionalism=Round(
                        Avg("ordergroup__orders__review__professionalism"),
                        1,
                    ),
                    communication=Round(
                        Avg("ordergroup__orders__review__communication"),
                        1,
                    ),
                    pricing=Round(
                        Avg("ordergroup__orders__review__pricing"),
                        1,
                    ),
                    timeliness=Round(
                        Avg("ordergroup__orders__review__timeliness"),
                        1,
                    ),
                )
                # Don't include rows with no reviews
                .filter(Q(rating__gt=0) | Q(negative_rating__gt=0))
                .order_by("-rating")
            )
        elif tab == "sellers":
            context["help_text"] = "Reviews of Sellers"
            reviews = (
                Seller.objects.values("id", "name")
                .annotate(
                    rating=Sum(
                        Case(
                            When(
                                seller_locations__seller_product_seller_locations__order_groups__orders__review__rating=True,
                                then=1,
                            ),
                            default=0,
                            output_field=IntegerField(),
                        )
                    ),
                    negative_rating=Sum(
                        Case(
                            When(
                                seller_locations__seller_product_seller_locations__order_groups__orders__review__rating=False,
                                then=1,
                            ),
                            default=0,
                            output_field=IntegerField(),
                        )
                    ),
                    # Round averages to 1 decimal place
                    professionalism=Round(
                        Avg(
                            "seller_locations__seller_product_seller_locations__order_groups__orders__review__professionalism"
                        ),
                        1,
                    ),
                    communication=Round(
                        Avg(
                            "seller_locations__seller_product_seller_locations__order_groups__orders__review__communication"
                        ),
                        1,
                    ),
                    pricing=Round(
                        Avg(
                            "seller_locations__seller_product_seller_locations__order_groups__orders__review__pricing"
                        ),
                        1,
                    ),
                    timeliness=Round(
                        Avg(
                            "seller_locations__seller_product_seller_locations__order_groups__orders__review__timeliness"
                        ),
                        1,
                    ),
                )
                # Don't include rows with no reviews
                .filter(Q(rating__gt=0) | Q(negative_rating__gt=0))
                .order_by("-rating")
            )
        else:
            # Default to all reviews
            reviews = (
                OrderReview.objects.all()
                .annotate(
                    user=Concat(
                        F("order__order_group__user__first_name"),
                        Value(" "),
                        F("order__order_group__user__last_name"),
                    ),
                    seller=F(
                        "order__order_group__seller_product_seller_location__seller_product__seller__name"
                    ),
                    product=F(
                        "order__order_group__seller_product_seller_location__seller_product__product__main_product__name"
                    ),
                    sum=(
                        # Treat null values as 0
                        Coalesce(F("professionalism"), Value(0))
                        + Coalesce(F("communication"), Value(0))
                        + Coalesce(F("pricing"), Value(0))
                        + Coalesce(F("timeliness"), Value(0))
                    ),
                    # This query gets the average rating based on four fields
                    avg=(
                        Case(
                            # If at least one field is not null, then calculate the average
                            When(
                                sum__gt=0,
                                # Get average rounded to 2 decimal places
                                then=Round(
                                    (F("sum"))
                                    / (
                                        # Get count of non-null fields for division
                                        Case(
                                            When(
                                                professionalism__isnull=True,
                                                then=0.0,
                                            ),
                                            default=1.0,
                                        )
                                        + Case(
                                            When(
                                                communication__isnull=True,
                                                then=0.0,
                                            ),
                                            default=1.0,
                                        )
                                        + Case(
                                            When(
                                                pricing__isnull=True,
                                                then=0.0,
                                            ),
                                            default=1.0,
                                        )
                                        + Case(
                                            When(
                                                timeliness__isnull=True,
                                                then=0.0,
                                            ),
                                            default=1.0,
                                        )
                                    ),
                                    2,
                                ),
                            ),
                        )
                    ),
                )
                .order_by("-created_on")
            )

        # Pagination
        paginator = Paginator(reviews, pagination_limit)
        page_obj = paginator.get_page(page_number)
        context["page_obj"] = page_obj

        if page_number is None:
            page_number = 1
        else:
            page_number = int(page_number)
        query_params["p"] = 1
        context["page_start_link"] = f"/customer/reviews/?{query_params.urlencode()}"
        query_params["p"] = page_number
        context["page_current_link"] = f"/customer/reviews/?{query_params.urlencode()}"

        if page_obj.has_previous():
            query_params["p"] = page_obj.previous_page_number()
            context["page_prev_link"] = f"/customer/reviews/?{query_params.urlencode()}"

        if page_obj.has_next():
            query_params["p"] = page_obj.next_page_number()
            context["page_next_link"] = f"/customer/reviews/?{query_params.urlencode()}"
        query_params["p"] = paginator.num_pages
        context["page_end_link"] = f"/customer/reviews/?{query_params.urlencode()}"

        return render(
            request, "customer_dashboard/snippets/reviews_table.html", context
        )

    query_params = request.GET.copy()
    if query_params.get("tab"):
        context["reviews_table_link"] = request.get_full_path()
    else:
        # Else load pending tab as default
        context["reviews_table_link"] = (
            f"{reverse('customer_reviews')}?{query_params.urlencode()}"
        )

    return render(request, "customer_dashboard/reviews.html", context)


def create_lead_board(leads):
    """
    Create a board structure from the given leads queryset.
    """
    # TODO: handle scale of leads (i.e. limit number of results, filter lanes)
    return [
        {
            "name": status_name,
            "value": status,
            "leads": [lead for lead in leads if lead.status == status],
        }
        for status, status_name in Lead.Status.get_ordered_choices()
    ]


@login_required(login_url="/admin/login/")
def leads(request):
    context = get_user_context(request)
    if not request.user.is_staff:
        return HttpResponseRedirect(reverse("customer_home"))

    context.update(
        {
            "selectable_statuses": [
                status[0] for status in UserSelectableLeadStatus.choices
            ],
            "lost_reasons": {
                value: text for value, text in Lead.LostReason.choices if value
            },
            "owners": User.sales_team_users.all(),
        }
    )

    return render(request, "customer_dashboard/leads/leads.html", context)


@login_required(login_url="/admin/login/")
def leads_board(request):
    context = {}
    if not request.user.is_staff:
        return HttpResponse("Unauthorized", status=401)

    if request.method == "POST":
        # Get filter parameters from the request
        owner_filter = request.POST.get("owned_by")
        est_conversion_filter = request.POST.get("est")

        if "update_status" in request.POST:
            lead_id = request.POST.get("lead_id")
            status = request.POST.get("status")
            if not Lead.objects.filter(id=lead_id).exists():
                return HttpResponse("Not found", status=404)

            lead = Lead.objects.get(id=lead_id)
            if status != lead.status:
                lead.status = status
                if status != Lead.Status.JUNK:
                    lead.lost_reason = None
                else:
                    lead.lost_reason = request.POST.get("lost_reason")
                try:
                    lead.clean()
                    lead.save()
                    # If status did not update due to expiration/conversion, then alert user
                    if status != lead.status and not lead.is_active:
                        messages.warning(request, "Lead was automatically closed.")
                except ValidationError as e:
                    messages.error(
                        request, f"Error updating lead: {','.join(e.messages)}"
                    )
        elif "new_card" in request.POST:
            form = NewLeadForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Lead created successfully.")
            else:
                messages.error(
                    request, f"Error creating lead. {form.non_field_errors().as_text()}"
                )
    else:
        # Get filter parameters from the request
        owner_filter = request.GET.get("owned_by")
        est_conversion_filter = request.GET.get("est")

    leads = Lead.objects.all().order_by("est_conversion_date", "-created_on")

    # Filter the queryset based on the filter parameters
    if owner_filter:
        if owner_filter == "unassigned":
            leads = leads.filter(owner__isnull=True)
        else:
            leads = leads.filter(owner=owner_filter)
    if est_conversion_filter:
        if est_conversion_filter == "today":
            leads = leads.filter(est_conversion_date=datetime.date.today())
        elif est_conversion_filter == "this_week":
            leads = leads.filter(
                est_conversion_date__week=datetime.date.today().isocalendar()[1]
            )
        elif est_conversion_filter == "this_month":
            leads = leads.filter(est_conversion_date__month=datetime.date.today().month)
        elif est_conversion_filter == "overdue":
            leads = leads.filter(est_conversion_date__lt=datetime.date.today())

    board = create_lead_board(leads)

    context.update(
        {
            "board": board,
            "owned_by": owner_filter,
            "est_conversion_filter": est_conversion_filter,
        }
    )

    return render(request, "customer_dashboard/leads/leads_kanban_board.html", context)


@login_required(login_url="/admin/login/")
def leads_card(request, lead_id):
    context = {}
    if not request.user.is_staff:
        return HttpResponse("Unauthorized", status=401)

    lead = Lead.objects.get(id=lead_id)

    if request.method == "POST":
        form = NewLeadForm(request.POST, instance=lead)
        if form.is_valid():
            lead = form.save()
            messages.success(request, "Lead saved successfully")
        else:
            # Reset the value of lead
            lead = Lead.objects.get(id=lead_id)
            messages.error(
                request, f"Error saving lead: {form.non_field_errors().as_text()}"
            )

    context.update({"lead": lead})

    return render(request, "customer_dashboard/leads/leads_kanban_card.html", context)


@login_required(login_url="/admin/login/")
def leads_card_edit(request, lead_id=None):
    context = {}
    if not request.user.is_staff:
        return HttpResponse("Unauthorized", status=401)

    if lead_id:
        if not Lead.objects.filter(id=lead_id).exists():
            return HttpResponse("Not found", status=404)

        lead = Lead.objects.get(id=lead_id)
        form = NewLeadForm(instance=lead)
    else:
        lead = None
        # Load New Lead form with Owner preset to current user if user is in sales team
        initial_data = (
            {"owner": request.user}
            if User.sales_team_users.filter(id=request.user.id).exists()
            else {}
        )
        form = NewLeadForm(initial=initial_data)

    context.update(
        {
            "form": form,
            "lead": lead,
        }
    )

    return render(
        request, "customer_dashboard/leads/leads_kanban_card_edit.html", context
    )


@login_required(login_url="/admin/login/")
def lead_detail(request, lead_id):
    context = {}
    context.update(get_user_context(request))

    if not request.user.is_staff:
        return HttpResponseRedirect(reverse("customer_home"))

    lead = Lead.objects.prefetch_related("notes").filter(id=lead_id).first()
    if not lead:
        messages.error(request, "Lead not found.")
        return HttpResponseRedirect(reverse("customer_leads"))

    lead_statuses = Lead.Status.get_ordered_choices()
    lead_form = LeadDetailForm(instance=lead)
    lead_note_queryset = lead.notes.order_by("created_on")

    LeadNoteFormset = inlineformset_factory(
        Lead,
        LeadNote,
        form=LeadNoteForm,
        formset=BaseLeadNoteFormset,
        extra=1,
    )
    lead_note_formset = LeadNoteFormset(
        instance=lead,
        queryset=lead_note_queryset,
    )

    if request.method == "POST":
        # Edit Details
        if "lead-form" in request.POST:
            lead_form = LeadDetailForm(request.POST, instance=lead)
            if lead_form.is_valid():
                if lead_form.has_changed():
                    lead = lead_form.save()
                    if lead.status != lead_form.instance.status:
                        messages.info(request, "Lead closed automatically.")
                    else:
                        messages.success(request, "Lead saved successfully.")
                else:
                    messages.info(request, "No changes detected.")
            else:
                messages.error(
                    request,
                    f"Error saving lead {lead_form.non_field_errors().as_text()}",
                )
                lead.refresh_from_db()

            # Reinitialize Form
            lead_form = LeadDetailForm(instance=lead)

        # Note Formset
        elif "note-formset" in request.POST:
            lead_note_formset = LeadNoteFormset(
                request.POST,
                instance=lead,
                queryset=lead_note_queryset,
            )
            action = request.POST.get("action", "create")

            if action == "create":
                # Handle creation
                for form in lead_note_formset.extra_forms:
                    if form.is_valid():
                        form.save()
                        messages.success(request, "Note added successfully.")
                        break
                    else:
                        messages.error(
                            request,
                            f"Error adding note: {form.non_field_errors().as_text()}",
                        )
                        break
            elif not (form_id := request.POST.get("form_id")) or not form_id.isdigit():
                messages.error(request, "Invalid form submission.")
            else:
                form_id = int(form_id)
                form = lead_note_formset.forms[form_id]
                if form.instance.created_by != request.user:
                    # Prevent other users from editing notes
                    messages.error(request, "Invalid form submission.")
                elif action == "edit":
                    # Handle editing
                    if form.has_changed():
                        if form.is_valid():
                            form.save()
                            messages.success(request, "Notes saved successfully.")
                        else:
                            messages.error(
                                request,
                                "Error saving notes. Please contact us if this continues.",
                            )
                    else:
                        messages.info(request, "No changes detected.")
                elif action == "delete":
                    # Handle deletion
                    if lead_note := LeadNote.objects.filter(
                        id=form.instance.id
                    ).first():
                        lead_note.delete()
                        messages.success(request, "Notes saved successfully.")
                    else:
                        messages.error(
                            request,
                            "Error saving notes. Please contact us if this continues.",
                        )
                else:
                    messages.error(request, "Invalid action.")

            # Reload formset
            lead_note_formset = LeadNoteFormset(
                instance=lead,
                queryset=lead_note_queryset,
            )

        # Mark as Junk
        elif "update_status" in request.POST:
            status = request.POST.get("status")
            if status != lead.status:
                lead.status = status
                if status != Lead.Status.JUNK:
                    lead.lost_reason = None
                else:
                    lead.lost_reason = request.POST.get("lost_reason")
                try:
                    lead.clean()
                    lead.save()
                    messages.success(request, "Status updated successfully.")
                except ValidationError as e:
                    messages.error(
                        request, f"Error updating status: {','.join(e.messages)}"
                    )
                    lead.refresh_from_db()

    context.update(
        {
            "lead": lead,
            "lead_form": lead_form,
            "lead_note_formset": lead_note_formset,
            "lead_statuses": lead_statuses,
            "lead_status_index": [status for (status, _) in lead_statuses].index(
                lead.status
            ),
            "lost_reasons": {
                value: label for (value, label) in Lead.LostReason.choices if value
            },
        }
    )

    return render(request, "customer_dashboard/leads/lead_detail.html", context)


def error_404(request, exception):
    context = {}
    context["exception"] = exception
    context["request"] = request
    return render(request, "customer_dashboard/404.html", context, status=404)


def error_500(request):
    context = {}
    context["request"] = request
    return render(request, "customer_dashboard/500.html", context, status=500)
