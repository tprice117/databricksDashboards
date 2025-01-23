import datetime
import logging
import time
from random import randint

import requests
import stripe
from django.conf import settings
from django.contrib import messages
from django.db.models import Avg, Count  # F, OuterRef, Q, Subquery, Sum,
from django.db.models.functions import Round
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django_filters import rest_framework as filters
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from requests import Response
from rest_framework import status, viewsets
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.filters import OrderFilterset, OrderGroupFilterset
from api.models.order.order_group_material import OrderGroupMaterial
from api.models.order.order_group_material_waste_type import OrderGroupMaterialWasteType
from api.models.order.order_group_service import OrderGroupService
from api.utils.denver_compliance_report import send_denver_compliance_report
from api.utils.utils import decrypt_string
from asset_management.models.asset import Asset
from billing.scheduled_jobs.attempt_charge_for_past_due_invoices import (
    attempt_charge_for_past_due_invoices,
)
from billing.scheduled_jobs.ensure_invoice_settings_default_payment_method import (
    ensure_invoice_settings_default_payment_method,
)
from billing.utils.billing import BillingUtils
from common.models.choices.user_type import UserType
from notifications.utils import internal_email
from payment_methods.utils.ds_payment_methods.ds_payment_methods import DSPaymentMethods

from .models import (
    AddOn,
    AddOnChoice,
    Advertisement,
    DayOfWeek,
    DisposalLocation,
    DisposalLocationWasteType,
    Industry,
    MainProduct,
    MainProductAddOn,
    MainProductCategory,
    MainProductCategoryGroup,
    MainProductCategoryInfo,
    MainProductInfo,
    MainProductServiceRecurringFrequency,
    MainProductWasteType,
    Order,
    OrderDisposalTicket,
    OrderGroup,
    OrderGroupAttachment,
    OrderLineItem,
    OrderLineItemType,
    Payout,
    Product,
    ProductAddOnChoice,
    Seller,
    SellerInvoicePayable,
    SellerInvoicePayableLineItem,
    SellerLocation,
    SellerProduct,
    SellerProductSellerLocation,
    SellerProductSellerLocationMaterial,
    SellerProductSellerLocationMaterialWasteType,
    SellerProductSellerLocationRental,
    SellerProductSellerLocationService,
    SellerProductSellerLocationServiceRecurringFrequency,
    ServiceRecurringFrequency,
    Subscription,
    TimeSlot,
    User,
    UserAddress,
    UserAddressType,
    UserGroup,
    UserGroupBilling,
    UserGroupCreditApplication,
    UserGroupLegal,
    UserUserAddress,
    WasteType,
)

# import pandas as pd
from .pricing_ml import pricing
from .serializers import (
    AddOnChoiceSerializer,
    AddOnSerializer,
    AdvertisementSerializer,
    AssetSerializer,
    DayOfWeekSerializer,
    DisposalLocationSerializer,
    DisposalLocationWasteTypeSerializer,
    IndustrySerializer,
    MainProductAddOnSerializer,
    MainProductCategoryGroupSerializer,
    MainProductCategoryInfoSerializer,
    MainProductCategorySerializer,
    MainProductInfoSerializer,
    MainProductSerializer,
    MainProductServiceRecurringFrequencySerializer,
    MainProductWasteTypeSerializer,
    OrderDisposalTicketSerializer,
    OrderGroupAttachmentSerializer,
    OrderGroupSerializer,
    OrderLineItemSerializer,
    OrderLineItemTypeSerializer,
    OrderSerializer,
    PayoutSerializer,
    ProductAddOnChoiceSerializer,
    ProductSerializer,
    SellerInvoicePayableLineItemSerializer,
    SellerInvoicePayableSerializer,
    SellerLocationSerializer,
    SellerProductSellerLocationMaterialSerializer,
    SellerProductSellerLocationMaterialWasteTypeSerializer,
    SellerProductSellerLocationRentalSerializer,
    SellerProductSellerLocationSerializer,
    SellerProductSellerLocationServiceRecurringFrequencySerializer,
    SellerProductSellerLocationServiceSerializer,
    SellerProductSerializer,
    SellerSerializer,
    ServiceRecurringFrequencySerializer,
    SubscriptionSerializer,
    TimeSlotSerializer,
    UserAddressSerializer,
    UserAddressTypeSerializer,
    UserGroupBillingSerializer,
    UserGroupCreditApplicationSerializer,
    UserGroupLegalSerializer,
    UserGroupSerializer,
    UserSerializer,
    UserUserAddressSerializer,
    WasteTypeSerializer,
)

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


class SpectacularAPIViewNoAuth(SpectacularAPIView):
    authentication_classes = []
    permission_classes = []


class SpectacularRedocViewNoAuth(SpectacularRedocView):
    authentication_classes = []
    permission_classes = []


class SpectacularSwaggerViewNoAuth(SpectacularSwaggerView):
    authentication_classes = []
    permission_classes = []


class AdvertisementViewSet(viewsets.ModelViewSet):
    queryset = Advertisement.objects.all()
    serializer_class = AdvertisementSerializer
    filterset_fields = ["id", "is_active"]


class SellerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Seller.objects.all()
    serializer_class = SellerSerializer
    filterset_fields = ["id"]

    def get_queryset(self):
        return self.queryset.prefetch_related("seller_products")


class SellerLocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SellerLocation.objects.all()
    serializer_class = SellerLocationSerializer
    filterset_fields = ["id", "seller"]


class UserAddressTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserAddressType.objects.all().order_by("sort")
    serializer_class = UserAddressTypeSerializer
    filterset_fields = ["id"]


class UserAddressViewSet(viewsets.ModelViewSet):
    queryset = UserAddress.objects.all()
    serializer_class = UserAddressSerializer
    filterset_fields = ["id"]

    def get_queryset(self):
        # Using queryset defined in api/managers/user_address.py
        return self.queryset.for_user(self.request.user)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["id", "user_id"]

    def get_queryset(self):
        # user_group__seller__seller_products
        self.queryset = self.queryset.select_related(
            "user_group__seller", "user_group__legal"
        )
        is_superuser = self.request.user == "ALL"

        if is_superuser:
            return self.queryset
        else:
            return self.queryset.filter(id=self.request.user.id)


class UserGroupViewSet(viewsets.ModelViewSet):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer
    filterset_fields = ["id", "share_code"]

    def get_queryset(self):
        # Allow search of all companies when share code or id is present.
        share_code = self.request.query_params.get("share_code", None)
        user_group_id = self.request.query_params.get("id", None)
        if share_code:
            return self.queryset.filter(share_code=share_code)
        elif user_group_id:
            return self.queryset.filter(id=user_group_id)
        else:
            is_superuser = self.request.user == "ALL" or (
                self.request.user.user_group.is_superuser
                if self.request.user and self.request.user.user_group
                else False
            )
            if is_superuser:
                return self.queryset
            else:
                return self.queryset.filter(id=self.request.user.user_group.id)


class UserGroupBillingViewSet(viewsets.ModelViewSet):
    queryset = UserGroupBilling.objects.all()
    serializer_class = UserGroupBillingSerializer

    def get_queryset(self):
        is_superuser = self.request.user == "ALL" or (
            self.request.user.user_group.is_superuser
            if self.request.user and self.request.user.user_group
            else False
        )
        if is_superuser:
            return self.queryset
        else:
            return self.queryset.filter(user_group=self.request.user.user_group)


class UserGroupLegalViewSet(viewsets.ModelViewSet):
    queryset = UserGroupLegal.objects.all()
    serializer_class = UserGroupLegalSerializer

    def get_queryset(self):
        is_superuser = self.request.user == "ALL" or (
            self.request.user.user_group.is_superuser
            if self.request.user and self.request.user.user_group
            else False
        )
        if is_superuser:
            return self.queryset
        else:
            return self.queryset.filter(user_group=self.request.user.user_group)


class UserGroupCreditApplicationViewSet(viewsets.ModelViewSet):
    queryset = UserGroupCreditApplication.objects.all()
    serializer_class = UserGroupCreditApplicationSerializer

    def get_queryset(self):
        is_superuser = self.request.user == "ALL" or (
            self.request.user.user_group.is_superuser
            if self.request.user and self.request.user.user_group
            else False
        )
        if is_superuser:
            return self.queryset
        else:
            return self.queryset.filter(user_group=self.request.user.user_group)


class UserUserAddressViewSet(viewsets.ModelViewSet):
    queryset = UserUserAddress.objects.all()
    serializer_class = UserUserAddressSerializer
    filterset_fields = ["id", "user", "user_address"]

    def get_queryset(self):
        is_superuser = self.request.user == "ALL" or (
            self.request.user.user_group.is_superuser
            if self.request.user and self.request.user.user_group
            else False
        )
        if is_superuser:
            return self.queryset
        elif self.request.user.type == UserType.ADMIN:
            users = User.objects.filter(user_group=self.request.user.user_group)
            return self.queryset.filter(user__in=users)
        else:
            return self.queryset.filter(user=self.request.user)


class AddOnChoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AddOnChoice.objects.all()
    serializer_class = AddOnChoiceSerializer
    filterset_fields = ["add_on", "add_on__main_product"]


@authentication_classes([])
@permission_classes([])
class AddOnViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AddOn.objects.all()
    serializer_class = AddOnSerializer
    filterset_fields = ["main_product"]


class DisposalLocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DisposalLocation.objects.all()
    serializer_class = DisposalLocationSerializer
    filterset_fields = ["id"]


class DisposalLocationWasteTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DisposalLocationWasteType.objects.all()
    serializer_class = DisposalLocationWasteTypeSerializer
    filterset_fields = ["id"]


@authentication_classes([])
@permission_classes([])
class IndustryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Industry.objects.all()
    serializer_class = IndustrySerializer
    filterset_fields = ["id", "name"]


@authentication_classes([])
@permission_classes([])
class MainProductCategoryGroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MainProductCategoryGroup.objects.all()
    serializer_class = MainProductCategoryGroupSerializer
    filterset_fields = ["id", "name"]


class MainProductAddOnViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MainProductAddOn.objects.all()
    serializer_class = MainProductAddOnSerializer
    filterset_fields = ["main_product", "add_on"]


@authentication_classes([])
@permission_classes([])
class MainProductCategoryInfoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MainProductCategoryInfo.objects.all()
    serializer_class = MainProductCategoryInfoSerializer
    filterset_fields = ["main_product_category"]


@authentication_classes([])
@permission_classes([])
class MainProductCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MainProductCategory.objects.all()
    serializer_class = MainProductCategorySerializer

    def get_queryset(self):
        return self.queryset.prefetch_related(
            "mainproductcategoryinfo_set",
            "industry",
        )


@authentication_classes([])
@permission_classes([])
class MainProductInfoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MainProductInfo.objects.all()
    serializer_class = MainProductInfoSerializer
    filterset_fields = ["main_product"]


@authentication_classes([])
@permission_classes([])
class MainProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MainProduct.objects.all()
    serializer_class = MainProductSerializer
    filterset_fields = ["id", "main_product_category__id", "is_related"]

    def get_queryset(self):
        return self.queryset.prefetch_related(
            "add_ons",
            "add_ons__choices",
            "images",
            "products__seller_products__seller_product_seller_locations",
            "products__seller_products__seller_product_seller_locations__order_groups__orders",
        )


@authentication_classes([])
@permission_classes([])
class MainProductWasteTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MainProductWasteType.objects.all()
    serializer_class = MainProductWasteTypeSerializer
    filterset_fields = ["main_product"]


class assetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer


class OrderGroupViewSet(viewsets.ModelViewSet):
    queryset = OrderGroup.objects.all()
    serializer_class = OrderGroupSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = OrderGroupFilterset

    def get_queryset(self):
        self.queryset = self.queryset.prefetch_related(
            "orders__order_line_items",
            "user__user_group__credit_applications",
            "seller_product_seller_location__seller_product__product__product_add_on_choices",
        )
        self.queryset = self.queryset.select_related(
            "user",
            "user__user_group",
            "user_address",
            "waste_type",
            "time_slot",
            "service_recurring_frequency",
            "seller_product_seller_location__seller_product__seller",
            "seller_product_seller_location__seller_product__product__main_product__main_product_category",
            "seller_product_seller_location__seller_location__seller",
        )
        if self.request.user == "ALL":
            return self.queryset
        elif self.request.user.type == UserType.ADMIN:
            return self.queryset.filter(user__user_group=self.request.user.user_group)
        else:
            return self.queryset.filter(user__id=self.request.user.id)


class OrderGroupAttachmentViewSet(viewsets.ModelViewSet):
    queryset = OrderGroupAttachment.objects.all()
    serializer_class = OrderGroupAttachmentSerializer
    filterset_fields = ["id", "order_group"]

    def get_queryset(self):
        # Only allow user to see their Company's attachments.
        return self.queryset.filter(
            order_group__user__user_group=self.request.user.user_group
        )


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = OrderFilterset

    def get_queryset(self):
        self.queryset = self.queryset.prefetch_related("order_line_items")
        self.queryset = self.queryset.select_related(
            "order_group__subscription",
        )
        if self.request.user == "ALL":
            return self.queryset
        elif self.request.user.type == UserType.ADMIN:
            return self.queryset.filter(
                order_group__user__user_group=self.request.user.user_group
            )
        else:
            return self.queryset.filter(order_group__user__id=self.request.user.id)


class OrderLineItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OrderLineItem.objects.all()
    serializer_class = OrderLineItemSerializer
    filterset_fields = ["id", "order"]


class OrderLineItemTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OrderLineItemType.objects.all()
    serializer_class = OrderLineItemTypeSerializer
    filterset_fields = ["id"]


class OrderDisposalTicketViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OrderDisposalTicket.objects.all()
    serializer_class = OrderDisposalTicketSerializer
    filterset_fields = ["id"]


class DayOfWeekViewSet(viewsets.ReadOnlyModelViewSet):  # added 2/25/2021
    queryset = DayOfWeek.objects.all()
    serializer_class = DayOfWeekSerializer
    filterset_fields = ["id"]


class TimeSlotViewSet(viewsets.ReadOnlyModelViewSet):  # added 2/25/2021
    queryset = TimeSlot.get_all_time_slots().order_by("-updated_on")
    serializer_class = TimeSlotSerializer
    filterset_fields = ["id"]


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):  # added 2/25/2021
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    filterset_fields = ["id"]


class PayoutViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payout.objects.all()
    serializer_class = PayoutSerializer
    filterset_fields = ["order"]


class ProductAddOnChoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductAddOnChoice.objects.all()
    serializer_class = ProductAddOnChoiceSerializer
    filterset_fields = ["product", "add_on_choice", "product__main_product"]


@authentication_classes([])
@permission_classes([])
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_fields = ["main_product"]

    def get_queryset(self):
        self.queryset = self.queryset.select_related(
            "main_product__main_product_category"
        )
        self.queryset = self.queryset.prefetch_related("product_add_on_choices")
        return self.queryset


class SellerProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SellerProduct.objects.all()
    serializer_class = SellerProductSerializer
    filterset_fields = ["seller", "product"]


class SellerProductSellerLocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SellerProductSellerLocation.objects.all()
    serializer_class = SellerProductSellerLocationSerializer
    filterset_fields = ["seller_product", "seller_location"]

    def get_queryset(self):
        self.queryset = self.queryset.prefetch_related(
            "seller_product__product__product_add_on_choices"
        )
        self.queryset = self.queryset.select_related(
            "seller_product__seller",
            "seller_product__product__main_product__main_product_category",
            "seller_location__seller",
            "service",
            "material",
            "rental",
        )
        return self.queryset


class SellerProductSellerLocationServiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SellerProductSellerLocationService.objects.all()
    serializer_class = SellerProductSellerLocationServiceSerializer
    filterset_fields = ["seller_product_seller_location"]

    def get_queryset(self):
        if self.request.user == "ALL":
            return self.queryset
        else:
            seller = (
                self.request.user.user_group.seller
                if self.request.user.user_group
                else None
            )
            return self.queryset.filter(
                seller_product_seller_location__seller_product__seller=seller
            )


class SellerInvoicePayableViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SellerInvoicePayable.objects.all()
    serializer_class = SellerInvoicePayableSerializer


class SellerInvoicePayableLineItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SellerInvoicePayableLineItem.objects.all()
    serializer_class = SellerInvoicePayableLineItemSerializer
    filterset_fields = ["order"]


class ServiceRecurringFrequencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceRecurringFrequency.objects.all()
    serializer_class = ServiceRecurringFrequencySerializer


class MainProductServiceRecurringFrequencyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MainProductServiceRecurringFrequency.objects.all()
    serializer_class = MainProductServiceRecurringFrequencySerializer


class SellerProductSellerLocationServiceRecurringFrequencyViewSet(
    viewsets.ReadOnlyModelViewSet
):
    queryset = SellerProductSellerLocationServiceRecurringFrequency.objects.all()
    serializer_class = SellerProductSellerLocationServiceRecurringFrequencySerializer

    def get_queryset(self):
        if self.request.user == "ALL":
            return self.queryset
        else:
            seller = (
                self.request.user.user_group.seller
                if self.request.user.user_group
                else None
            )
            return self.queryset.filter(
                seller_product_seller_location_service__seller_product_seller_location__seller_product__seller=seller
            )


class SellerProductSellerLocationRentalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SellerProductSellerLocationRental.objects.all()
    serializer_class = SellerProductSellerLocationRentalSerializer
    filterset_fields = ["seller_product_seller_location"]

    def get_queryset(self):
        if self.request.user == "ALL":
            return self.queryset
        else:
            seller = (
                self.request.user.user_group.seller
                if self.request.user.user_group
                else None
            )
            return self.queryset.filter(
                seller_product_seller_location__seller_product__seller=seller
            )


class SellerProductSellerLocationMaterialViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SellerProductSellerLocationMaterial.objects.all()
    serializer_class = SellerProductSellerLocationMaterialSerializer
    filterset_fields = ["seller_product_seller_location"]

    def get_queryset(self):
        if self.request.user == "ALL":
            return self.queryset
        else:
            seller = (
                self.request.user.user_group.seller
                if self.request.user.user_group
                else None
            )
            return self.queryset.filter(
                seller_product_seller_location__seller_product__seller=seller
            )


class SellerProductSellerLocationMaterialWasteTypeViewSet(
    viewsets.ReadOnlyModelViewSet
):
    queryset = SellerProductSellerLocationMaterialWasteType.objects.all()
    serializer_class = SellerProductSellerLocationMaterialWasteTypeSerializer
    filterset_fields = [
        "seller_product_seller_location_material",
        "main_product_waste_type",
    ]

    def get_queryset(self):
        if self.request.user == "ALL":
            return self.queryset
        else:
            seller = (
                self.request.user.user_group.seller
                if self.request.user.user_group
                else None
            )
            return self.queryset.filter(
                seller_product_seller_location_material__seller_product_seller_location__seller_product__seller=seller
            )


@authentication_classes([])
@permission_classes([])
class WasteTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WasteType.objects.all()
    serializer_class = WasteTypeSerializer


# Use-case-specific model views.
class UserAddressesForSellerViewSet(viewsets.ModelViewSet):
    queryset = UserAddress.objects.all()
    serializer_class = UserAddressSerializer

    def get_queryset(self):
        seller = (
            self.request.user.user_group.seller
            if self.request.user.user_group
            else None
        )
        seller_order_user_address_ids = (
            OrderGroup.objects.filter(
                seller_product_seller_location__seller_product__seller=seller
            ).values_list("user_address__id", flat=True)
            if seller
            else []
        )
        return self.queryset.filter(id__in=seller_order_user_address_ids)


class OrderGroupsForSellerViewSet(viewsets.ModelViewSet):
    queryset = OrderGroup.objects.all()
    serializer_class = OrderGroupSerializer

    def get_queryset(self):
        seller = (
            self.request.user.user_group.seller
            if self.request.user.user_group
            else None
        )
        return (
            self.queryset.filter(
                seller_product_seller_location__seller_product__seller=seller
            )
            if seller
            else []
        )


class OrdersForSellerViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_queryset(self):
        seller = (
            self.request.user.user_group.seller
            if self.request.user.user_group
            else None
        )
        return (
            self.queryset.filter(
                order_group__seller_product_seller_location__seller_product__seller=seller
            )
            if seller
            else []
        )


baseUrl = "https://api.thetrashgurus.com/v2/"
MAX_RETRIES = 5
API_KEY = "556b608df74309034553676f5d4425401ae6c2fc29db793a5b1501"


def call_TG_API(url, payload):
    attempt_num = 0  # keep track of how many times we've retried
    while attempt_num < MAX_RETRIES:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            return Response(data, status=status.HTTP_200_OK)
        else:
            attempt_num += 1
            # You can probably use a logger to log the error here
            time.sleep(5)  # Wait for 5 seconds before re-trying
    return Response({"error": "Request failed"}, status=response.status_code)


def get(endpoint, body):
    url = baseUrl + endpoint
    # payload = {"api_key": API_KEY} | body
    payload = dict({"api_key": API_KEY}.items() | body.items())
    return call_TG_API(url, payload)


def post(endpoint, body):
    url = baseUrl + endpoint
    payload = {**{"api_key": API_KEY}, **body}
    print(payload)
    return call_TG_API(url, payload)


def put(endpoint, body):
    url = baseUrl + endpoint
    payload = dict({"api_key": API_KEY}.items() | body.items())
    return call_TG_API(url, payload)


def delete(endpoint, body):
    url = baseUrl + endpoint
    payload = dict({"api_key": API_KEY}.items() | body.items())
    return call_TG_API(url, payload)


# Pricing Endpoint.
@api_view(["POST"])
def get_pricing(request):
    price_mod = pricing.Price_Model(
        data={
            "seller_location": (
                request.data["seller_location"]
                if "seller_location" in request.data
                else None
            ),
            "product": request.data["product"],
            "user_address": request.data["user_address"],
            "waste_type": request.data["waste_type"],
        }
    )

    # Get SellerLocations that offer the product.
    seller_products = SellerProduct.objects.filter(product=request.data["product"])
    seller_product_seller_locations = SellerProductSellerLocation.objects.filter(
        seller_product__in=seller_products, active=True
    )

    return Response(price_mod.get_prices(seller_product_seller_locations))


# ml views for pricing
class Prediction(APIView):
    def post(self, request):
        # Load the model
        price_mod = MlConfig.regressor
        enc = MlConfig.encoder
        # initialize the modeler
        modeler = xgb.price_model_xgb(price_mod, enc)
        # get the data from the request and predict
        pred = modeler.predict_price(input_data=request.data)
        response_dict = {"Price": pred}
        return Response(response_dict)


class TaskView(APIView):
    def get(self, request, pk=None, *args, **kwargs):
        if pk or request.query_params.get("job_id"):
            ids = []
            ids.append(int(pk or request.query_params.get("job_id")))
            return post("get_job_details", {"job_ids": ids, "include_task_history": 0})
        if request.query_params.get("customer_id"):
            return post(
                "get_all_tasks",
                {
                    "job_type": 3,
                    "customer_id": int(request.query_params.get("customer_id")),
                },
            )
        else:
            response = post("get_all_tasks", {"job_type": 3, "is_pagination": 0})
            new_list = []
            for data in response.data["data"]:
                new_list.append({**data, **{"time_start": 0, "time_end": 0}})
            response.data["data"] = new_list
            return response

    def post(self, request, *args, **kwargs):
        # account = Account.objects.get(id=request.data["customer_comment"])
        # job_delivery_datetime = parse_datetime(request.data["job_delivery_datetime"])
        # job_pickup_datetime = parse_datetime(request.data["job_pickup_datetime"])
        new_data = {
            **request.data,
            # **{
            #   "customer_username": account.name,
            #   "customer_phone": account.phone or "1234567890",
            #   "customer_address": account.shipping_street + ", " + account.shipping_city + ", " + account.shipping_state,
            #   "latitude": str(account.shipping_latitude),
            #   "longitude": str(account.shipping_longitude),
            #   # "job_pickup_datetime": job_pickup_datetime.strftime("%Y-%m-%d") + " " + str(request.data["time_start"]).zfill(2) + ":00:00",
            #   # "job_delivery_datetime": job_delivery_datetime.strftime("%Y-%m-%d") + " " + str(request.data["time_end"]).zfill(2) + ":00:00",
            #    "job_pickup_datetime": job_pickup_datetime.strftime("%Y-%m-%d") + " " + str(request.data["time_start"]).zfill(2) + ":00:00",
            #   "job_delivery_datetime": job_delivery_datetime.strftime("%Y-%m-%d") + " " + str(request.data["time_end"]).zfill(2) + ":00:00",
            #   "has_pickup": "0",
            #   "has_delivery": "0",
            #   "layout_type": "1",
            #   "tracking_link": 1,
            #   "auto_assignment": "0",
            #   "notify": 1,
            #   "tags":"",
            #   "geofence":0,
            # }
        }
        return post("create_task", new_data)

    def put(self, request, pk=None, *args, **kwargs):
        player_object = self.get_object(pk or request.query_params.get("id"))
        return put("edit_task", request.data)

    def delete(self, request, pk=None, *args, **kwargs):
        return delete("delete_task", {"job_id": pk or request.query_params.get("id")})


class AgentView(APIView):
    def get(self, request, pk=None, *args, **kwargs):
        if pk or request.query_params.get("id"):
            return post(
                "view_fleet_profile", {"fleet_id": pk or request.query_params.get("id")}
            )
        else:
            response = get("get_all_fleets", {})
            new_list = []
            for data in response.data["data"]:
                new_list.append({**data, **{"team_id": 0, "first_name": ""}})
            response.data["data"] = new_list
            return response

    def post(self, request, *args, **kwargs):
        return post("add_agent", request.data)

    def put(self, request, pk=None, *args, **kwargs):
        player_object = self.get_object(pk or request.query_params.get("id"))
        return put("edit_agent", request.data)

    def delete(self, request, pk=None, *args, **kwargs):
        return delete(
            "delete_fleet_account", {"team_id": pk or request.query_params.get("id")}
        )


class TeamView(APIView):
    def get(self, request, pk=None, *args, **kwargs):
        if pk or request.query_params.get("id"):
            return post("view_teams", {"team_id": pk or request.query_params.get("id")})
        else:
            return get("view_all_team_only", {})

    def post(self, request, *args, **kwargs):
        return post("create_team", request.data)

    def put(self, request, pk=None, *args, **kwargs):
        player_object = self.get_object(pk or request.query_params.get("id"))
        return put("update_team", request.data)

    def delete(self, request, pk=None, *args, **kwargs):
        return delete("delete_team", {"team_id": pk or request.query_params.get("id")})


class ManagerView(APIView):
    def get(self, request, pk=None, *args, **kwargs):
        return get("view_all_manager")

    def post(self, request, *args, **kwargs):
        return post("add_manager", request.data)

    def delete(self, request, pk=None, *args, **kwargs):
        return delete(
            "delete_manager", {"dispatcher_id": pk or request.query_params.get("id")}
        )


class CustomerView(APIView):
    def get(self, request, pk=None, *args, **kwargs):
        if pk or request.query_params.get("id"):
            return post(
                "view_customer_profile",
                {"customer_id": pk or request.query_params.get("id")},
            )
        else:
            return get("get_all_customers", {})

    def post(self, request, *args, **kwargs):
        return post(
            "customer/add",
            {
                "user_type": 0,
                "name": request.data["customer_email"],
                "email": request.data["customer_email"],
                "phone": randint(1000000000, 9999999999),
            },
        )

    def put(self, request, pk=None, *args, **kwargs):
        player_object = self.get_object(pk or request.query_params.get("id"))
        return put("customer/edit", request.data)

    def delete(self, request, pk=None, *args, **kwargs):
        return delete(
            "delete_customer", {"customer_id": pk or request.query_params.get("id")}
        )


class MerchantView(APIView):
    def post(self, request, *args, **kwargs):
        return post("merchant/sign_up", request.data)

    def put(self, request, pk=None, *args, **kwargs):
        player_object = self.get_object(pk or request.query_params.get("id"))
        return put("merchant/edit_merchant", request.data)

    def delete(self, request, pk=None, *args, **kwargs):
        return delete(
            "merchant/delete", {"merchant_id": pk or request.query_params.get("id")}
        )


class MissionView(APIView):
    def get(self, request, pk=None, *args, **kwargs):
        return get("get_mission_list")

    def post(self, request, *args, **kwargs):
        return post("create_mission_task", request.data)

    def delete(self, request, pk=None, *args, **kwargs):
        return delete(
            "delete_mission", {"mission_id": pk or request.query_params.get("id")}
        )


class ConvertSFOrderToScrapTask(APIView):
    def get(self, request, pk=None, *args, **kwargs):
        order = Order.objects.get(order_number=pk)
        account = Account.objects.get(id=order.account_id)
        service_provider = Order.objects.get(id=order.service_provider)
        return post(
            "create_task",
            {
                "order_id": order.order_number,
                "customer_username": account.name,
                "customer_phone": account.phone or "1234567890",
                "customer_address": account.shipping_street
                + ", "
                + account.shipping_city
                + ", "
                + account.shipping_state,
                "latitude": str(account.shipping_latitude),
                "longitude": str(account.shipping_longitude),
                "job_pickup_datetime": order.start_date_time.strftime(
                    "%Y-%m-%d %H:%m:%s"
                ),  # add field to salesforce object
                "job_delivery_datetime": order.start_date_time.strftime(
                    "%Y-%m-%d %H:%m:%s"
                ),  # add field to salesforce object
                "has_pickup": "0",
                "has_delivery": "0",
                "layout_type": "1",
                "tracking_link": 1,
                "auto_assignment": "0",
                "timezone": "-420",
                "notify": 1,
                "tags": "",
                "geofence": 0,
                "team_id": service_provider.scrap_team_id,
                "fleet_id": service_provider.scrap_fleet_id,
            },
        )


# Stripe Views


@api_view(["GET"])
def stripe_customer_portal_url(request, user_address_id):
    user_address = UserAddress.objects.get(id=user_address_id)

    billing_portal_session = stripe.billing_portal.Session.create(
        configuration=(
            settings.STRIPE_PAYMENT_METHOD_CUSTOMER_PORTAL_CONFIG
            if request.GET.get("only_payments", False) == "true"
            else settings.STRIPE_FULL_CUSTOMER_PORTAL_CONFIG
        ),
        customer=user_address.stripe_customer_id,
    )

    return Response({"url": billing_portal_session.url})


class StripePaymentMethods(APIView):
    def get(self, request, format=None):
        stripe_customer_id = self.request.query_params.get("id")
        print(stripe_customer_id)
        payment_methods = stripe.Customer.list_payment_methods(
            stripe_customer_id,
            type="card",
        )
        return Response(payment_methods)


class StripeSetupIntents(APIView):
    def get(self, request, format=None):
        stripe_customer_id = self.request.query_params.get("id")

        # Create Setup Intent.
        setup_intent = stripe.SetupIntent.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            usage="off_session",
        )

        # Create ephemeral key and add to reponse.
        ephemeralKey = stripe.EphemeralKey.create(
            customer=stripe_customer_id,
            stripe_version="2020-08-27",
        )
        setup_intent["ephemeral_key"] = ephemeralKey.secret
        return Response(setup_intent)


class StripePaymentIntents(APIView):
    def get(self, request, format=None):
        stripe_customer_id = self.request.query_params.get("customer_id")
        amount = self.request.query_params.get("amount")

        # Create Setup Intent.
        payment_intent = stripe.PaymentIntent.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            amount=amount,
            currency="usd",
        )

        # Create ephemeral key and add to reponse.
        ephemeralKey = stripe.EphemeralKey.create(
            customer=stripe_customer_id,
            stripe_version="2020-08-27",
        )
        payment_intent["ephemeral_key"] = ephemeralKey.secret
        return Response(payment_intent)


class StripeCreateCheckoutSession(APIView):
    def get(self, request, format=None):
        customer_id = self.request.query_params.get("customer_id")
        price_id = self.request.query_params.get("price_id")
        mode = self.request.query_params.get("mode")

        session = stripe.checkout.Session.create(
            customer=customer_id,
            success_url="https://success.com",
            cancel_url="https://cancel.com",
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                },
            ],
            mode=mode,
        )
        return Response(session)


class StripeConnectPayoutForService(APIView):
    # Payout Accepted Vendor for Service Request.
    def get(self, request, pk, format=None):
        service_request = ServiceRequest.objects.get(pk=pk)

        # Get accpeted quote (will error if more than 1 accepted).
        accepted_quote = service_request.quotes.get(accepted=True)

        # Calculate the total amount_received for this service request.
        payment_intents = stripe.PaymentIntent.search(
            query='metadata["service_request_id"]:"' + str(service_request.id) + '"'
        )
        total_received = sum(
            payment_intent.amount_received for payment_intent in payment_intents
        )

        # Calculate the total amount payed out to the vendor.
        transfers = stripe.Transfer.list(transfer_group=str(service_request.id))
        total_transferred = sum(transfer.amount for transfer in transfers)

        # Calculate Hohm fee.
        customer_fee_ratio = service_request.platform_fee / 100
        vendor_fee_ratio = accepted_quote.platform_fee / 100

        customer_fee_dollar = total_received * customer_fee_ratio
        vendor_fee_dollar = (total_received - customer_fee_dollar) * vendor_fee_ratio
        total_platform_fee_dollar = customer_fee_dollar + vendor_fee_dollar

        # Transfer remaining vendor-payout (considering what has already been transffered).
        total_payout = total_received - total_platform_fee_dollar
        remaining_transfer_amount = total_payout - total_transferred
        if round(remaining_transfer_amount) > 1:
            transfer = stripe.Transfer.create(
                amount=round(remaining_transfer_amount),
                currency="usd",
                destination=accepted_quote.vendor.connect_express_account_id,
                transfer_group=service_request.id,
            )
            return Response(transfer)
        else:
            return Response()


# Stripe Dashboarding (GET only endpoints)


class StripeConnectAccount(APIView):
    def get(self, request, format=None):
        has_more = True
        starting_after = None
        data = []
        while has_more:
            accounts = stripe.Account.list(limit=100, starting_after=starting_after)
            data = data + accounts["data"]
            has_more = accounts["has_more"]
            starting_after = data[-1]["id"]
        return Response(data)


class StripeConnectTransfer(APIView):
    def get(self, request, format=None):
        has_more = True
        starting_after = None
        data = []
        while has_more:
            transfers = stripe.Transfer.list(limit=100, starting_after=starting_after)
            data = data + transfers["data"]
            has_more = transfers["has_more"]
            starting_after = data[-1]["id"]
        return Response(data)


class StripeBillingInvoice(APIView):
    def get(self, request, format=None):
        has_more = True
        starting_after = None
        data = []
        while has_more:
            invoices = stripe.Invoice.list(limit=100, starting_after=starting_after)
            data = data + invoices["data"]
            has_more = invoices["has_more"]
            starting_after = data[-1]["id"]
        return Response(data)


class StripeBillingSubscription(APIView):
    def get(self, request, format=None):
        has_more = True
        starting_after = None
        data = []
        while has_more:
            subscriptions = stripe.Subscription.list(
                limit=100, starting_after=starting_after
            )
            data = data + subscriptions["data"]
            has_more = subscriptions["has_more"]
            starting_after = data[-1]["id"]
        return Response(data)


class StripeCorePaymentIntents(APIView):
    def get(self, request, format=None):
        has_more = True
        starting_after = None
        data = []
        while has_more:
            payment_intents = stripe.PaymentIntent.list(
                limit=100, starting_after=starting_after
            )
            data = data + payment_intents["data"]
            has_more = payment_intents["has_more"]
            starting_after = data[-1]["id"]
        return Response(data)


class StripeCoreBalance(APIView):
    def get(self, request, format=None):
        balance = stripe.Balance.retrieve()
        return Response(balance)


class StripeCoreBalanceTransactions(APIView):
    def get(self, request, format=None):
        has_more = True
        starting_after = None
        data = []
        while has_more:
            payment_intents = stripe.BalanceTransaction.list(
                limit=100, starting_after=starting_after
            )
            data = data + payment_intents["data"]
            has_more = payment_intents["has_more"]
            starting_after = data[-1]["id"]
        return Response(data)


class StripeBillingInvoiceItems(APIView):
    def get(self, request, format=None):
        has_more = True
        starting_after = None
        data = []
        while has_more:
            invoice_items = stripe.InvoiceItem.list(
                limit=100, starting_after=starting_after
            )
            data = data + invoice_items["data"]
            has_more = invoice_items["has_more"]
            starting_after = data[-1]["id"]
        return Response(data)


# Denver Waste Compliance Report.
@api_view(["POST"])
def denver_compliance_report(request):
    try:
        user_address_id = request.data["user_address"]
        send_denver_compliance_report(user_address_id, request.user.id)
    except Exception as error:
        print("An exception occurred: {}".format(error.text))
        logger.error(f"denver_compliance_report: [{error}]", exc_info=error)

    return Response("Success", status=200)


# Feature-based views.
@api_view(["GET"])
def get_user_group_credit_status(request):
    user_group = request.user.user_group

    # Compute credit status.
    if user_group and user_group.credit_status:
        return Response(user_group.credit_status, status=200)
    else:
        return Response("No credit status found.", status=200)


@api_view(["POST"])
def submit_order(request):
    order = Order.objects.get(pk=request.data["order_id"])
    order.submitted_on = datetime.datetime.now()
    order.save()

    return Response("Success", status=200)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def order_status_view(request, order_id):
    key = request.query_params.get("key", "")
    try:
        params = decrypt_string(key)
    except Exception as e:
        params = ""
        logger.error(f"order_status_view: [{e}]", exc_info=e)
    if str(params) == str(order_id):
        order = Order.objects.get(id=order_id)
        accept_url = f"/api/order/{order_id}/accept/?key={key}"
        # deny_url = f"/api/order/{order_id}/deny/?key={key}"
        deny_url = reverse("supplier_bookings")
        payload = {"order": order, "accept_url": accept_url, "deny_url": deny_url}
        return render(request, "notifications/emails/supplier_email.min.html", payload)
    else:
        return render(
            request,
            "notifications/emails/failover_email_us.html",
            {"subject": f"Supplier%20Approved%20%5B{order_id}%5D"},
        )


@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([])
def update_order_status(request, order_id, accept=True):
    key = request.query_params.get("key", "")
    try:
        params = decrypt_string(key)
        if str(params) == str(order_id):
            order = Order.objects.get(id=order_id)
            if order.status == Order.Status.PENDING:
                if accept:
                    order.status = Order.Status.SCHEDULED
                    order.save()
                else:
                    # Send internal email to notify of denial.
                    internal_email.supplier_denied_order(order)
        else:
            raise ValueError("Invalid Token")
    except Exception as e:
        logger.error(f"update_order_status: [{e}]", exc_info=e)
        return render(
            request,
            "notifications/emails/failover_email_us.html",
            {"subject": f"Supplier%20Approved%20%5B{order_id}%5D"},
        )
    if request.method == "POST":
        # This is an HTMX request, so respond with html snippet
        return render(
            request,
            "supplier_dashboard/snippets/order_status.html",
            {"order": order},
        )
    else:
        # This is a GET request, so render a full success page.
        return render(
            request,
            "notifications/emails/supplier_order_updated.html",
            {"order_id": order_id},
        )


@csrf_exempt
@api_view(["GET"])
def create_products_for_main_product(request, main_product_id):
    main_product = MainProduct.objects.get(id=main_product_id)

    # Create the MainProduct's Products.
    Product.create_products_for_main_product(main_product)

    messages.success(
        request,
        "Successfully created products for main product: {}".format(main_product.name),
    )

    return redirect(
        "admin:api_mainproduct_change",
        main_product_id,
    )


def apple_app_site_association(request):
    # Get the apple-app-site-association file.
    apple_app_site_association_file = open(
        settings.BASE_DIR / ".well-known/apple_app_site_association.json", "r"
    )
    # Return the file.
    return HttpResponse(
        apple_app_site_association_file.read(), content_type="application/json"
    )


def asset_link(request):
    # Get the assetlinks.json file.
    asset_link_file = open(settings.BASE_DIR / ".well-known/assetlinks.json", "r")
    # Return the file.
    return HttpResponse(asset_link_file.read(), content_type="application/json")


def test3(request):
    order = Order.objects.get(id="8362a2e7-bc0c-4388-8a37-777451e65845")

    invoice = BillingUtils.get_or_create_invoice_for_user_address(
        order.order_group.user_address,
        is_cart=False,
        is_booking=False,
    )

    print("invoice: ", invoice)

    BillingUtils.create_invoice_items_for_order(
        invoice=invoice,
        order=order,
    )

    return HttpResponse(status=200)


def test2(request):
    # Get all Stripe invoices that are "open".
    has_more = True
    starting_after = None
    next_page = None
    data = []
    while has_more:
        if next_page:
            invoices = stripe.Invoice.search(
                query='status:"open"', limit=100, page=next_page
            )
        else:
            invoices = stripe.Invoice.search(query='status:"open"', limit=100)

        data = data + invoices["data"]
        has_more = invoices["has_more"]
        next_page = invoices["next_page"]
    print(len(data))

    print(data)

    for invoice in data:
        if (
            not "user_group_id" in invoice["metadata"]
            and UserGroupBilling.objects.filter(
                email=invoice["customer_email"]
            ).exists()
        ):
            print(
                invoice["id"],
                " | ",
                invoice["customer_email"] + " | ",
                UserGroupBilling.objects.filter(email=invoice["customer_email"])
                .first()
                .email,
            )

        # if (
        #     not "user_group_id" in invoice["metadata"]
        #     and UserAddress.objects.filter(
        #         stripe_customer_id=invoice["customer"]
        #     ).exists()
        # ):
        #     print(invoice["id"])
        #     user_address = UserAddress.objects.filter(
        #         stripe_customer_id=invoice["customer"]
        #     ).first()
        #     if user_address.user_group:
        #         stripe.Invoice.modify(
        #             invoice["id"],
        #             metadata={
        #                 "user_group_id": user_address.user_group.id,
        #                 "user_address_id": user_address.id,
        #             },
        #         )

    # # Finalize all invoices.
    # for invoice_id in data:
    #     try:
    #         print("Finalizing invoice: {}".format(invoice_id))
    #         stripe.Invoice.send_invoice(
    #             invoice_id,
    #         )
    #         print("Finalized invoice: {}".format(invoice_id))
    #     except Exception as error:
    #         print("An exception occurred: {}".format(str(error)))
    #     print("------------------------------------")
    # return
    # # Get all OrderLineItems that are not equal to "BYPASS".
    # order_line_items = OrderLineItem.objects.filter(
    #     stripe_invoice_line_item_id__isnull=False
    # ).exclude(stripe_invoice_line_item_id="BYPASS")

    # for order_line_item in order_line_items:
    #     order_line_item.stripe_invoice_line_item_id = None
    #     order_line_item.save()
    #     print(
    #         order_line_item.order.id,
    #         " | ",
    #         order_line_item.id,
    #         " | ",
    #         order_line_item.stripe_invoice_line_item_id,
    # )

    # Get all order line items.
    order_line_items = OrderLineItem.objects.filter(
        stripe_invoice_line_item_id__isnull=False,
        order__end_date__lte=datetime.datetime(2023, 12, 31),
    ).exclude(stripe_invoice_line_item_id="BYPASS")

    # Get all Invoice Items from Stripe.
    print("Getting all invoice items from Stripe.")
    has_more = True
    starting_after = None
    data = []
    while has_more:
        invoice_items = stripe.InvoiceItem.list(
            limit=100, starting_after=starting_after
        )
        data = data + invoice_items["data"]
        has_more = invoice_items["has_more"]
        starting_after = data[-1]["id"]
    invoice_items = data

    # Get all invoice items created on or after 12/31/2023.
    print("Getting all invoice items created on or after 12/31/2023.")
    # invoice_items = [
    #     invoice_item
    #     for invoice_item in invoice_items
    #     if datetime.datetime.fromtimestamp(invoice_item["date"])
    #     >= datetime.datetime(2023, 12, 31)
    # ]
    print(len(order_line_items))
    print(len(invoice_items))

    # Get all invoice ids for all OrderLineItems.
    invoice_ids = []
    for order_line_item in order_line_items:
        invoice_line_items = [
            invoice_item
            for invoice_item in invoice_items
            if "order_line_item_id" in invoice_item["metadata"]
            and invoice_item["metadata"]["order_line_item_id"]
            == str(order_line_item.id)
        ]

        if len(invoice_line_items) != 1:
            invoice_line_items_to_delete = [
                invoice_item
                for invoice_item in invoice_line_items
                if invoice_item["id"] != order_line_item.stripe_invoice_line_item_id
            ]
            for invoice_line_item_to_delete in invoice_line_items_to_delete:
                if (
                    invoice_line_item_to_delete["id"]
                    != order_line_item.stripe_invoice_line_item_id
                ):
                    # stripe.InvoiceItem.delete(invoice_line_item_to_delete["id"])
                    print(
                        order_line_item.id,
                        " | ",
                        order_line_item.stripe_invoice_line_item_id,
                        " | ",
                        [
                            invoice_line_item["id"]
                            for invoice_line_item in invoice_line_items
                        ],
                        " | ",
                        invoice_line_item_to_delete["id"],
                        " | ",
                        len(invoice_line_items),
                    )
        # invoice_item = next(
        #     (
        #         x
        #         for x in invoice_items
        #         if x["id"] == order_line_item.stripe_invoice_line_item_id
        #     ),
        #     None,
        # )

    #     # if invoice_item:
    #     #     invoice_ids.append(invoice_item.invoice)
    #     #     print(
    #     #         order_line_item.order.id,
    #     #         " | ",
    #     #         order_line_item.id,
    #     #         " | ",
    #     #         invoice_item.invoice,
    #     #     )

    # # Get all invoice items that are associated to an invoice.
    # invoice_items_with_invoice = []
    # invoice_ids = [invoice.id for invoice in invoices]
    # print(invoice_ids)
    # for invoice_item in invoice_items:
    #     # Print the index of the invoice item.
    #     # print()
    #     if invoice_item["invoice"] in invoice_ids:
    #         invoice_items_with_invoice.append(invoice_item)

    # print(invoice_items_with_invoice)
