import calendar
import csv
from typing import List

import requests
import stripe
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.models import Group
from django.contrib.auth.models import User as DjangoUser
from django.forms import HiddenInput
from django.shortcuts import redirect, render
from django.urls import path
from django.utils.html import format_html

from api.utils.checkbook_io import CheckbookIO

from .forms import *
from .models import *

stripe.api_key = settings.STRIPE_SECRET_KEY


# Filters.
class CreatedDateFilter(SimpleListFilter):
    title = "Creation Date"
    parameter_name = "created_on"

    def lookups(self, request, model_admin):
        return [
            ("today", "Today"),
            ("yesterday", "Yesterday"),
            ("7d", "Last 7 Days"),
            ("1m", "This Month"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "Today":
            return queryset.filter(created_on__date=datetime.date.today())
        elif self.value() == "Yesterday":
            return queryset.filter(
                created_on__date=datetime.date.today() - datetime.timedelta(days=1)
            )
        elif self.value() == "Last 7 Days":
            return queryset.filter(
                created_on__date__gte=datetime.date.today() - datetime.timedelta(days=7)
            )
        elif self.value() == "This Month":
            return queryset.filter(
                created_on__date__gte=datetime.date.today().replace(day=1)
            )


class UserGroupTypeFilter(SimpleListFilter):
    title = "Type"
    parameter_name = "type"

    def lookups(self, request, model_admin):
        return [
            ("seller", "Seller"),
            ("customer", "Customer"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "seller":
            return queryset.filter(seller__isnull=False)
        elif self.value() == "customer":
            return queryset.filter(seller__isnull=True)


# Inlines.
class AddOnChoiceInline(admin.TabularInline):
    model = AddOnChoice
    fields = ("name",)
    show_change_link = True
    extra = 0


class MainProductCategoryInfoInline(admin.TabularInline):
    model = MainProductCategoryInfo
    fields = ("name",)
    show_change_link = True
    extra = 0


class MainProductInline(admin.TabularInline):
    model = MainProduct
    fields = ("name",)
    show_change_link = True
    extra = 0


class MainProductInfoInline(admin.TabularInline):
    model = MainProductInfo
    fields = ("name",)
    show_change_link = True
    extra = 0


class OrderGroupServiceInline(admin.TabularInline):
    model = OrderGroupService
    fields = ("rate", "miles")
    show_change_link = True
    extra = 0


class OrderGroupRentalInline(admin.TabularInline):
    model = OrderGroupRental
    fields = ("included_days", "price_per_day_included", "price_per_day_additional")
    show_change_link = True
    extra = 0


class OrderGroupMaterialInline(admin.TabularInline):
    model = OrderGroupMaterial
    fields = ("price_per_ton", "tonnage_included")
    show_change_link = True
    extra = 0


class OrderInline(admin.TabularInline):
    model = Order
    fields = ("start_date", "end_date", "service_date", "submitted_on")
    show_change_link = True
    extra = 0


class SubscriptionInline(admin.StackedInline):
    model = Subscription
    fields = ("frequency", "service_day")
    show_change_link = True
    extra = 0


class ProductInline(admin.TabularInline):
    model = Product
    fields = ("product_code", "description")
    show_change_link = True
    extra = 0


class ProductAddOnChoiceInline(admin.TabularInline):
    model = ProductAddOnChoice
    fields = ("name", "product", "add_on_choice")
    show_change_link = True
    extra = 0


class SellerLocationInline(admin.TabularInline):
    model = SellerLocation
    fields = ("name",)
    show_change_link = True
    extra = 0


class SellerLocationMailingAddressInline(admin.StackedInline):
    model = SellerLocationMailingAddress
    fields = ("street", "city", "state", "postal_code", "country")
    show_change_link = True
    extra = 0


class SellerProductInline(admin.TabularInline):
    model = SellerProduct
    fields = ("product",)
    show_change_link = True
    extra = 0


class SellerProductSellerLocationInline(admin.TabularInline):
    model = SellerProductSellerLocation
    fields = ("seller_product", "total_inventory")
    show_change_link = True
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super(SellerProductSellerLocationInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        if db_field.name == "seller_product":
            if request._obj_ is not None:
                print(request._obj_)
                print(field.queryset)
                field.queryset = field.queryset.filter(seller=request._obj_.seller)
            else:
                field.queryset = field.queryset.none()
        return field


class SellerProductSellerLocationServiceInline(admin.StackedInline):
    model = SellerProductSellerLocationService
    show_change_link = True
    extra = 0


class SellerProductSellerLocationServiceRecurringFrequencyInline(admin.StackedInline):
    model = SellerProductSellerLocationServiceRecurringFrequency
    show_change_link = True
    extra = 0


class SellerProductSellerLocationRentalInline(admin.StackedInline):
    model = SellerProductSellerLocationRental
    show_change_link = True
    extra = 0


class SellerProductSellerLocationMaterialInline(admin.StackedInline):
    model = SellerProductSellerLocationMaterial
    show_change_link = True
    extra = 0


class SellerProductSellerLocationMaterialWasteTypeInline(admin.StackedInline):
    model = SellerProductSellerLocationMaterialWasteType
    show_change_link = True
    extra = 0


class UserGroupBillingInline(admin.StackedInline):
    model = UserGroupBilling
    fields = ("email", "street", "city", "state", "postal_code", "country")
    show_change_link = True
    extra = 0


class UserGroupLegalInline(admin.StackedInline):
    model = UserGroupLegal
    fields = (
        "name",
        "doing_business_as",
        "structure",
        "industry",
        "street",
        "city",
        "state",
        "postal_code",
        "country",
    )
    show_change_link = True
    extra = 0


class UserGroupCreditApplicationInline(admin.TabularInline):
    model = UserGroupCreditApplication
    fields = ("requested_credit_limit", "created_on")
    readonly_fields = ("requested_credit_limit", "created_on")
    show_change_link = False
    extra = 0


class UserGroupUserInline(admin.TabularInline):
    model = UserGroupUser
    fields = ("user_group", "user")
    show_change_link = True
    extra = 0


class UserInline(admin.TabularInline):
    model = User
    fields = (
        "is_admin",
        "first_name",
        "last_name",
        "email",
        "phone",
    )
    readonly_fields = ("first_name", "last_name", "email", "phone")
    show_change_link = True
    extra = 0


class OrderLineItemInlineForm(forms.ModelForm):
    seller_payout_price = forms.CharField(required=False, disabled=True)
    customer_price = forms.CharField(required=False, disabled=True)
    is_paid = forms.BooleanField(required=False, disabled=True)

    class Meta:
        model = OrderLineItem
        fields = (
            "order_line_item_type",
            "rate",
            "quantity",
            "seller_payout_price",
            "platform_fee_percent",
            "customer_price",
            "is_paid",
            "stripe_invoice_line_item_id",
        )
        readonly_fields = (
            "seller_payout_price",
            "customer_price",
            "is_paid",
            "stripe_invoice_line_item_id",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        order_line_item: OrderLineItem = self.instance
        if order_line_item and order_line_item.stripe_invoice_line_item_id:
            # If the OrderLineItem has a Stripe Invoice Line Item ID, then make it read-only.
            for f in self.fields:
                self.fields[f].disabled = True

        # Set initial values for read-only fields.
        self.initial["seller_payout_price"] = order_line_item.seller_payout_price()
        self.initial["customer_price"] = order_line_item.customer_price()
        self.initial["is_paid"] = (
            order_line_item.payment_status() == OrderLineItem.PaymentStatus.PAID
        )


class OrderLineItemInline(admin.TabularInline):
    model = OrderLineItem
    form = OrderLineItemInlineForm
    show_change_link = True
    extra = 0


class OrderDisposalTicketInline(admin.TabularInline):
    model = OrderDisposalTicket
    fields = ("ticket_id", "disposal_location", "waste_type", "weight")
    show_change_link = True
    extra = 0


class PayoutInline(admin.TabularInline):
    model = Payout
    fields = (
        "amount",
        "description",
        "stripe_transfer_id",
        "checkbook_payout_id",
    )
    show_change_link = True
    extra = 0
    can_delete = False


class SellerInvoicePayableLineItemInline(admin.TabularInline):
    model = SellerInvoicePayableLineItem
    fields = ("order", "amount", "description")
    autocomplete_fields = [
        "order",
    ]
    show_change_link = True
    extra = 0


# class SellerInvoicePayableItemReadOnlyInline(admin.TabularInline):
#     model = SellerInvoicePayableLineItem
#     fields = ('amount', 'description')
#     readonly_fields = ('amount', 'description')
#     extra=0

#     def has_add_permission(self, request, obj):
#         return False


class AddOnChoiceAdmin(admin.ModelAdmin):
    search_fields = ["name", "add_on__name"]
    list_display = ("name", "add_on")


class AddOnAdmin(admin.ModelAdmin):
    inlines = [
        AddOnChoiceInline,
    ]


class MainProductCategoryAdmin(admin.ModelAdmin):
    inlines = [
        MainProductInline,
        MainProductCategoryInfoInline,
    ]


class ProductAdmin(admin.ModelAdmin):
    search_fields = ["description", "main_product__name"]
    list_display = ("__str__", "main_product")
    inlines = [
        ProductAddOnChoiceInline,
    ]


class MainProductAdmin(admin.ModelAdmin):
    search_fields = ["name", "main_product_category__name"]
    list_display = ("name", "main_product_category", "sort")
    inlines = [
        ProductInline,
        MainProductInfoInline,
    ]


class MainProductInfoAdmin(admin.ModelAdmin):
    search_fields = ["name", "main_product__name"]
    list_display = ("name", "main_product")


class SellerAdmin(admin.ModelAdmin):
    search_fields = [
        "name",
    ]
    inlines = [
        SellerProductInline,
        SellerLocationInline,
    ]

    change_list_template = "admin/entities/seller_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("import-csv/", self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode("utf-8").splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            keys = [
                "name",
                "phone",
                "website",
                "type_display",
                "location_type",
                "status",
                "lead_time_hrs",
                "marketplace_display_name",
                "location_logo_url",
                "badge",
            ]
            for row in reader:
                print(row.keys())
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(
                        request,
                        "Your csv file must have a header rows with 'name', 'phone', 'website', 'type_display', 'location_type', 'status', 'lead_time_hrs', 'marketplace_display_name', 'location_logo_url', and 'badge' as the first columns.",
                    )
                    return redirect("..")

            # Create User Groups.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                print(row)
                if Seller.objects.filter(name=row["name"]).count() == 0:
                    test, test2 = Seller.objects.get_or_create(
                        name=row["name"],
                        phone=row["phone"],
                        website=row["website"],
                        type_display=row["type_display"],
                        location_type=row["location_type"],
                        status=row["status"],
                        lead_time_hrs=row["lead_time_hrs"],
                        marketplace_display_name=row["marketplace_display_name"],
                        location_logo_url=row["location_logo_url"],
                        badge=row["badge"],
                    )
                    print(test)
                    print(test2)
                else:
                    print("USER ALREADY EXISITS: " + row["name"])

            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)


class SellerLocationAdmin(admin.ModelAdmin):
    search_fields = ["name", "seller__name"]
    list_display = (
        "name",
        "seller",
        "total_seller_payout_price",
        "total_paid_to_seller",
        "payout_status",
        "total_invoiced_from_seller",
        "seller_invoice_status",
    )
    inlines = [
        SellerLocationMailingAddressInline,
        SellerProductSellerLocationInline,
    ]

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj
        return super(SellerLocationAdmin, self).get_form(request, obj, **kwargs)

    def total_paid_to_seller(self, obj):
        payout_line_items = Payout.objects.filter(
            order__order_group__seller_product_seller_location__seller_location=obj
        )
        return sum(
            [payout_line_items.amount for payout_line_items in payout_line_items]
        )

    def total_seller_payout_price(self, obj):
        order_line_items = OrderLineItem.objects.filter(
            order__order_group__seller_product_seller_location__seller_location=obj
        )
        return round(
            sum(
                [
                    order_line_item.rate * order_line_item.quantity
                    for order_line_item in order_line_items
                ]
            ),
            2,
        )

    def payout_status(self, obj):
        payout_diff = self.total_seller_payout_price(obj) - self.total_paid_to_seller(
            obj
        )
        if payout_diff == 0:
            return format_html("<p>&#128994;</p>")
        elif payout_diff > 0:
            return format_html("<p>&#128993;</p>")
        else:
            return format_html("<p>&#128308;</p>")

    def total_invoiced_from_seller(self, obj):
        seller_invoice_payable_line_items = SellerInvoicePayableLineItem.objects.filter(
            order__order_group__seller_product_seller_location__seller_location=obj
        )
        return sum(
            [
                seller_invoice_payable_line_items.amount
                for seller_invoice_payable_line_items in seller_invoice_payable_line_items
            ]
        )

    def seller_invoice_status(self, obj):
        payout_diff = self.total_invoiced_from_seller(obj) - self.total_paid_to_seller(
            obj
        )
        if payout_diff == 0:
            return format_html("<p>&#128994;</p>")
        elif payout_diff >= 0:
            return format_html("<p>&#128993;</p>")
        else:
            return format_html("<p>&#128308;</p>")

    change_list_template = "admin/entities/seller_location_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("import-csv/", self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode("utf-8").splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            keys = [
                "seller_id",
                "name",
                "street",
                "city",
                "state",
                "postal_code",
                "country",
                "stripe_connect_account_id",
            ]
            for row in reader:
                print(row.keys())
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(
                        request,
                        "Your csv file must have a header rows with 'seller_id', 'name', 'street', 'city', 'state', 'postal_code', 'country', and 'stripe_connect_account_id' as the first columns.",
                    )
                    return redirect("..")

            # Create User Groups.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                print(row)
                if SellerLocation.objects.filter(name=row["name"]).count() == 0:
                    test, test2 = SellerLocation.objects.get_or_create(
                        seller=Seller.objects.get(id=row["seller_id"]),
                        name=row["name"],
                        street=row["street"],
                        city=row["city"],
                        state=row["state"],
                        postal_code=row["postal_code"],
                        country=row["country"],
                        stripe_connect_account_id=row["stripe_connect_account_id"],
                    )
                    print(test)
                    print(test2)
                else:
                    print("USER ALREADY EXISITS: " + row["name"])

            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)


class SellerProductAdmin(admin.ModelAdmin):
    search_fields = ["product__product_code", "seller__name"]
    list_display = ("product", "seller")
    list_filter = ("product__main_product__main_product_category", "seller")

    change_list_template = "admin/entities/seller_product_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("import-csv/", self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode("utf-8").splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            keys = ["seller_id", "product_id"]
            for row in reader:
                print(row.keys())
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(
                        request,
                        "Your csv file must have a header rows with 'seller_id', 'product_id' as the first columns.",
                    )
                    return redirect("..")

            # Create SellerProduct.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                print(row)
                does_exist = (
                    SellerProduct.objects.filter(
                        seller=Seller.objects.get(id=row["seller_id"]),
                        product=Product.objects.get(id=row["product_id"]),
                    ).count()
                    > 0
                )

                if not does_exist:
                    test, test2 = SellerProduct.objects.get_or_create(
                        seller=Seller.objects.get(id=row["seller_id"]),
                        product=Product.objects.get(id=row["product_id"]),
                    )
                    print(test)
                    print(test2)
                else:
                    print("SellerProduct ALREADY EXISITS")

            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)


class SellerProductSellerLocationAdmin(admin.ModelAdmin):
    search_fields = [
        "seller_location__name",
        "seller_location__seller__name",
        "seller_product__product__main_product__name",
    ]
    list_display = ("seller_product", "seller_location", "get_seller")
    autocomplete_fields = ["seller_product", "seller_location"]
    list_filter = (
        "seller_product__product__main_product__main_product_category",
        "seller_location__seller",
    )
    inlines = [
        SellerProductSellerLocationServiceInline,
        SellerProductSellerLocationRentalInline,
        SellerProductSellerLocationMaterialInline,
    ]

    @admin.display(description="Seller")
    def get_seller(self, obj):
        return obj.seller_location.seller

    change_list_template = (
        "admin/entities/seller_product_seller_location_changelist.html"
    )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("import-csv/", self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode("utf-8").splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            keys = [
                "id",
                "seller_product_id",
                "seller_location_id",
                "total_inventory",
                "min_price",
                "max_price",
                "service_radius",
                "delivery_fee",
                "removal_fee",
                "fuel_environmental_markup",
            ]
            for row in reader:
                print(row.keys())
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(
                        request,
                        "Your csv file must have a header rows with 'id', 'seller_product_id', 'seller_location_id', 'total_inventory', 'min_price', 'max_price', 'service_radius', 'delivery_fee', 'removal_fee', and 'fuel_environmental_markup' as the first columns.",
                    )
                    return redirect("..")

            # Create SellerProduct.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                does_exist = (
                    SellerProductSellerLocation.objects.filter(
                        seller_product=SellerProduct.objects.get(
                            id=row["seller_product_id"]
                        ),
                        seller_location=SellerLocation.objects.get(
                            id=row["seller_location_id"]
                        ),
                    ).count()
                    > 0
                )

                if row["id"] == "" and not does_exist:
                    # Create SellerProductSellerLocation.
                    test, test2 = SellerProductSellerLocation.objects.get_or_create(
                        seller_product=SellerProduct.objects.get(
                            id=row["seller_product_id"]
                        ),
                        seller_location=SellerLocation.objects.get(
                            id=row["seller_location_id"]
                        ),
                    )
                elif row["id"] != "" and does_exist:
                    seller_product_seller_location = (
                        SellerProductSellerLocation.objects.get(id=row["id"])
                    )
                    seller_product_seller_location.total_inventory = row[
                        "total_inventory"
                    ]
                    seller_product_seller_location.min_price = row["min_price"]
                    seller_product_seller_location.max_price = row["max_price"]
                    seller_product_seller_location.service_radius = row[
                        "service_radius"
                    ]
                    seller_product_seller_location.delivery_fee = row["delivery_fee"]
                    seller_product_seller_location.removal_fee = row["removal_fee"]
                    seller_product_seller_location.fuel_environmental_markup = row[
                        "fuel_environmental_markup"
                    ]
                    seller_product_seller_location.save()
                else:
                    print("SellerProductSellerLocation ALREADY EXISITS")

            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)


class SellerProductSellerLocationServiceAdmin(admin.ModelAdmin):
    inlines = [
        SellerProductSellerLocationServiceRecurringFrequencyInline,
    ]

    change_list_template = (
        "admin/entities/seller_product_seller_location_service_changelist.html"
    )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("import-csv/", self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode("utf-8").splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            keys = [
                "seller_product_seller_location_id",
                "price_per_mile",
                "flat_rate_price",
            ]
            for row in reader:
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(
                        request,
                        "Your csv file must have a header rows with 'seller_product_seller_location_id', 'price_per_mile', and 'flat_rate_price' as the first columns.",
                    )
                    return redirect("..")

            # Create SellerProduct.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                try:
                    seller_product_seller_location = (
                        SellerProductSellerLocation.objects.get(
                            id=row["seller_product_seller_location_id"]
                        )
                    )
                    does_exist = (
                        SellerProductSellerLocationService.objects.filter(
                            seller_product_seller_location=seller_product_seller_location,
                        ).count()
                        > 0
                    )

                    if not does_exist:
                        # Create SellerProductSellerLocation.
                        (
                            test,
                            test2,
                        ) = SellerProductSellerLocationService.objects.get_or_create(
                            seller_product_seller_location=SellerProductSellerLocation.objects.get(
                                id=row["seller_product_seller_location_id"]
                            ),
                            price_per_mile=None,
                            flat_rate_price=row["flat_rate_price"],
                        )
                    else:
                        service = SellerProductSellerLocationService.objects.get(
                            seller_product_seller_location=seller_product_seller_location,
                        )
                        service.price_per_mile = None
                        service.flat_rate_price = row["flat_rate_price"]
                        service.save()
                except Exception as ex:
                    print("Error: " + str(ex))

            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)


class SellerProductSellerLocationMaterialAdmin(admin.ModelAdmin):
    inlines = [
        SellerProductSellerLocationMaterialWasteTypeInline,
    ]


class UserAddressAdmin(admin.ModelAdmin):
    model = UserAddress
    list_display = ("name", "user_group", "project_id")
    autocomplete_fields = ["user_group", "user"]
    search_fields = ["name", "street"]


class UserAdmin(admin.ModelAdmin):
    model = User
    search_fields = ["email", "first_name", "last_name"]
    list_display = ("email", "first_name", "last_name", "cart_orders", "active_orders")
    autocomplete_fields = ["user_group"]
    list_filter = (CreatedDateFilter, "user_group")
    inlines = [
        UserGroupUserInline,
    ]

    def cart_orders(self, obj):
        return Order.objects.filter(order_group__user=obj, submitted_on=None).count()

    def active_orders(self, obj):
        return (
            Order.objects.filter(order_group__user=obj)
            .exclude(submitted_on=None)
            .count()
        )

    change_list_template = "admin/entities/user_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("import-csv/", self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode("utf-8").splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            keys = ["user_group", "phone", "email", "first_name", "last_name"]
            for row in reader:
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(
                        request,
                        "Your csv file must have a header rows with 'user_group', 'phone', 'email', 'first_name', and 'last_name' as the first columns.",
                    )
                    return redirect("..")

            # Create User Groups.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                print(row)
                if User.objects.filter(email=row["email"]).count() == 0:
                    test, test2 = User.objects.get_or_create(
                        user_group=UserGroup.objects.get(id=row["user_group"]),
                        user_id="",
                        phone=row["phone"],
                        email=row["email"],
                        first_name=row["first_name"],
                        last_name=row["last_name"],
                        is_admin=True,
                    )
                    print(test)
                    print(test2)
                else:
                    print("USER ALREADY EXISITS: " + row["email"])

            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)


class UserGroupAdmin(admin.ModelAdmin):
    model = UserGroup
    list_display = (
        "name",
        "seller",
        "user_count",
        "seller_locations",
        "seller_product_seller_locations",
        "credit_utilization",
    )
    search_fields = ["name"]
    list_filter = (UserGroupTypeFilter,)
    inlines = [
        UserGroupBillingInline,
        UserGroupLegalInline,
        UserGroupCreditApplicationInline,
        UserInline,
    ]

    change_list_template = "admin/entities/user_group_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("import-csv/", self.import_csv),
        ]
        return my_urls + urls

    def user_count(self, obj):
        return obj.user_set.count()

    def seller_locations(self, obj):
        # Get all SellerLocations for this UserGroup.
        return obj.seller.seller_locations.count() if obj.seller else None

    def seller_product_seller_locations(self, obj):
        # Get all SellerProductSellerLocations for this UserGroup.
        seller_locations = obj.seller.seller_locations.all() if obj.seller else None
        return (
            sum(
                [
                    seller_location.seller_location_seller_products.count()
                    for seller_location in seller_locations
                ]
            )
            if seller_locations
            else None
        )

    def credit_utilization(self, obj: UserGroup):
        return f"{float(obj.credit_limit_used()) / float((obj.credit_line_limit or 0.0) + 0.0000000001)}%"

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode("utf-8").splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            for row in reader:
                if not "name" in row.keys():
                    self.message_user(
                        request,
                        "Your csv file must have a header row with 'name' as the first column.",
                    )
                    return redirect("..")

            # Create User Groups.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                print(row)
                test, test2 = UserGroup.objects.get_or_create(
                    name=row["name"],
                )
                print(test)
                print(test2)

            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)


class OrderGroupAdmin(admin.ModelAdmin):
    model = OrderGroup
    list_display = ("user", "user_address", "seller_product_seller_location")
    list_filter = (CreatedDateFilter,)
    autocomplete_fields = [
        "seller_product_seller_location",
    ]
    inlines = [
        SubscriptionInline,
        OrderInline,
        OrderGroupServiceInline,
        OrderGroupRentalInline,
        OrderGroupMaterialInline,
    ]


class OrderAdmin(admin.ModelAdmin):
    model = Order
    readonly_fields = ("auto_order_type", "customer_price", "seller_price")
    search_fields = ("id",)
    list_display = (
        "order_group",
        "start_date",
        "end_date",
        "auto_order_type",
        "status",
        "service_date",
        "customer_price",
        "customer_invoiced",
        "customer_paid",
        "payment_status",
        "seller_price",
        "total_paid_to_seller",
        "payout_status",
        "total_invoiced_from_seller",
        "seller_invoice_status",
    )
    list_filter = (
        "status",
        CreatedDateFilter,
    )
    inlines = [
        OrderLineItemInline,
        OrderDisposalTicketInline,
        PayoutInline,
        SellerInvoicePayableLineItemInline,
    ]
    actions = ["send_payouts", "create_draft_invoices"]

    def auto_order_type(self, obj: Order):
        return obj.get_order_type()

    @admin.action(description="Create draft invoices")
    def create_draft_invoices(self, request, queryset):
        # Get distinct UserAddresses.
        distinct_user_addresses: List[UserAddress] = []
        for order in queryset:
            user_address = order.order_group.user_address
            current_user_address_ids = [
                user_address.id for user_address in distinct_user_addresses
            ]
            if user_address.id not in current_user_address_ids:
                distinct_user_addresses.append(user_address)

        # For each UserAddress, create or update invoices for all orders.
        for user_address in distinct_user_addresses:
            # Check if UserAddress has a Stripe Customer ID.
            # If not, create a Stripe Customer.
            if not user_address.stripe_customer_id:
                stripe_customer = stripe.Customer.create(
                    email=user_address.user.email,
                    name=user_address.name,
                )
                user_address.stripe_customer_id = stripe_customer.id
                user_address.save()

            orders_for_user_address = queryset.filter(
                order_group__user_address=user_address
            )

            # Get the current draft invoice or create a new one.
            draft_invoices = stripe.Invoice.search(
                query='customer:"'
                + user_address.stripe_customer_id
                + '" AND status:"draft"',
            )
            if len(draft_invoices) > 0:
                stripe_invoice = draft_invoices["data"][0]
            else:
                stripe_invoice = stripe.Invoice.create(
                    customer=user_address.stripe_customer_id,
                    auto_advance=False,
                )

            # Enable automatic taxes on the invoice.
            stripe.Invoice.modify(
                stripe_invoice.id,
                automatic_tax={
                    "enabled": True,
                },
            )

            # Loop through each order and add any OrderLineItems that don't have
            # a StripeInvoiceLineItemId on the OrderLineItem.
            order: Order
            for order in orders_for_user_address:
                # Get existing Stripe Invoice Summary Item(s) for this [Order].
                stripe_invoice_summary_items_response = requests.get(
                    "https://api.stripe.com/v1/invoices/"
                    + stripe_invoice.id
                    + "/summary_items",
                    headers={
                        "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
                    },
                )
                stripe_invoice_summary_items = (
                    stripe_invoice_summary_items_response.json()["data"]
                )

                # Ensure we have a Stripe Invoice Summary Item for this [Order].
                # If order.stripe_invoice_summary_item_id is None, then create a new one.
                if any(
                    x["description"] == order.stripe_invoice_summary_item_description()
                    for x in stripe_invoice_summary_items
                ):
                    stripe_invoice_summary_item = next(
                        (
                            item
                            for item in stripe_invoice_summary_items
                            if item["description"]
                            == order.stripe_invoice_summary_item_description()
                        ),
                        None,
                    )
                else:
                    new_summary_invoice_summary_item_response = requests.post(
                        "https://api.stripe.com/v1/invoices/"
                        + stripe_invoice.id
                        + "/summary_items",
                        headers={
                            "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                        data={
                            "description": order.stripe_invoice_summary_item_description(),
                        },
                    )
                    stripe_invoice_summary_item = (
                        new_summary_invoice_summary_item_response.json()
                    )

                # Get OrderLineItems that don't have a StripeInvoiceLineItemId.
                order_line_items = OrderLineItem.objects.filter(
                    order=order,
                    stripe_invoice_line_item_id=None,
                )

                # Create Stripe Invoice Line Item for each OrderLineItem that
                # doesn't have a StripeInvoiceLineItemId.
                order_line_item: OrderLineItem
                for order_line_item in order_line_items:
                    # Create Stripe Invoice Line Item.
                    stripe_invoice_line_item = stripe.InvoiceItem.create(
                        customer=order.order_group.user_address.stripe_customer_id,
                        invoice=stripe_invoice.id,
                        description=order_line_item.order_line_item_type.name
                        + " | Qty: "
                        + str(order_line_item.quantity)
                        + " @ $"
                        + str(
                            round(
                                order_line_item.customer_price()
                                / order_line_item.quantity,
                                2,
                            )
                        )
                        + "/unit",
                        amount=round(100 * order_line_item.customer_price()),
                        tax_behavior="exclusive",
                        tax_code=order_line_item.order_line_item_type.stripe_tax_code_id,
                        currency="usd",
                        period={
                            "start": calendar.timegm(order.start_date.timetuple()),
                            "end": calendar.timegm(order.end_date.timetuple()),
                        },
                        metadata={
                            "order_line_item_id": order_line_item.id,
                            "main_product_name": order.order_group.seller_product_seller_location.seller_product.product.main_product.name,
                            "order_start_date": order.start_date.strftime("%a, %b %-d"),
                            "order_end_date": order.end_date.strftime("%a, %b %-d"),
                        },
                    )

                    # Update OrderLineItem with StripeInvoiceLineItemId.
                    order_line_item.stripe_invoice_line_item_id = (
                        stripe_invoice_line_item.id
                    )
                    order_line_item.save()

                    # Get all Stripe Invoice Items for this Stripe Invoice.
                    stripe_invoice_items_response = requests.get(
                        f"https://api.stripe.com/v1/invoices/{stripe_invoice.id}/lines",
                        headers={
                            "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
                        },
                    )

                    # Get the Stripe Invoice Item for this OrderLineItem.
                    stripe_invoice_items = stripe_invoice_items_response.json()["data"]
                    stripe_invoice_item = next(
                        (
                            item
                            for item in stripe_invoice_items
                            if item["metadata"]["order_line_item_id"]
                            and item["metadata"]["order_line_item_id"]
                            == str(order_line_item.id)
                        ),
                        None,
                    )

                    # Add Stripe Invoice Line Item to Stripe Invoice Summary Item.
                    if stripe_invoice_item:
                        response = requests.post(
                            f"https://api.stripe.com/v1/invoices/{stripe_invoice.id}/lines/{stripe_invoice_item['id']}",
                            headers={
                                "Authorization": "Bearer " + settings.STRIPE_SECRET_KEY,
                                "Content-Type": "application/x-www-form-urlencoded",
                            },
                            data={
                                "rendering[summary_item]": stripe_invoice_summary_item[
                                    "id"
                                ],
                            },
                        )
                        print(response.json())

        messages.success(
            request, "Successfully created/updated invoices for all selected orders."
        )

    @admin.action(description="Send payouts")
    def send_payouts(self, request, queryset):
        # Get distinct SellerLocations.
        distinct_seller_locations: List[SellerLocation] = []
        for order in queryset:
            seller_location = (
                order.order_group.seller_product_seller_location.seller_location
            )
            current_seller_location_ids = [
                seller_location.id for seller_location in distinct_seller_locations
            ]
            if seller_location.id not in current_seller_location_ids:
                distinct_seller_locations.append(seller_location)

        # For each SellerLocation, send payouts for all orders.
        for seller_location in distinct_seller_locations:
            orders_for_seller_location = queryset.filter(
                order_group__seller_product_seller_location__seller_location=seller_location
            )

            if seller_location.stripe_connect_account_id:
                print("Payout via Stripe")
                # If connected with Stripe Connnect, payout via Stripe.
                for order in orders_for_seller_location:
                    # Only send payout if seller has a Stripe Connect Account.
                    payout_diff = self.seller_price(order) - self.total_paid_to_seller(
                        order
                    )
                    if payout_diff > 0:
                        try:
                            # Payout via Stripe.
                            transfer = stripe.Transfer.create(
                                amount=round(payout_diff * 100),
                                currency="usd",
                                destination=order.order_group.seller_product_seller_location.seller_location.stripe_connect_account_id,
                            )

                            # Save Payout.
                            Payout.objects.create(
                                order=order,
                                amount=payout_diff,
                                stripe_transfer_id=transfer.id,
                            )
                        except Exception as ex:
                            print("Error: " + str(ex))
            elif seller_location.payee_name and hasattr(
                seller_location, "mailing_address"
            ):
                print("Payout via Checkbook")
                # If not connected with Stripe Connect, but [payee_name] and
                # [mailing_address] are set, payout via Checkbook.
                amount_to_send = 0

                # Compute total amount to be sent.
                for order in orders_for_seller_location:
                    payout_diff = self.seller_price(order) - self.total_paid_to_seller(
                        order
                    )
                    if payout_diff > 0:
                        amount_to_send += payout_diff

                # Send payout via Checkbook.
                if amount_to_send > 0:
                    check_number = CheckbookIO().sendPhysicalCheck(
                        seller_location=seller_location,
                        amount=amount_to_send,
                        orders=orders_for_seller_location,
                    )

                # Save Payout for each order.
                for order in orders_for_seller_location:
                    payout_diff = self.seller_price(order) - self.total_paid_to_seller(
                        order
                    )
                    if payout_diff > 0:
                        Payout.objects.create(
                            order=order,
                            amount=payout_diff,
                            checkbook_payout_id=check_number,
                        )

        messages.success(request, "Successfully paid out all selected orders.")

    def customer_price(self, obj):
        return round(obj.customer_price(), 2)

    def seller_price(self, obj):
        return round(obj.seller_price(), 2)

    def customer_invoiced(self, obj: Order):
        invoiced_order_line_items = obj.order_line_items.filter(
            stripe_invoice_line_item_id__isnull=False
        )

        total_invoiced = 0
        order_line_item: OrderLineItem
        for order_line_item in invoiced_order_line_items:
            total_invoiced += order_line_item.customer_price()
        return total_invoiced

    def customer_paid(self, obj):
        invoiced_order_line_items = obj.order_line_items.filter(
            stripe_invoice_line_item_id__isnull=False
        )

        total_paid = 0
        order_line_item: OrderLineItem
        for order_line_item in invoiced_order_line_items:
            total_paid += (
                order_line_item.customer_price()
                if order_line_item.payment_status() == OrderLineItem.PaymentStatus.PAID
                else 0
            )
        return total_paid

    def payment_status(self, obj):
        payout_diff = self.customer_invoiced(obj) - self.customer_paid(obj)
        if payout_diff == 0:
            return format_html("<p>&#128994;</p>")
        elif payout_diff > 0:
            return format_html("<p>&#128308;</p>")
        else:
            return format_html("<p>&#128993;</p>")

    def total_paid_to_seller(self, obj):
        payouts = Payout.objects.filter(order=obj)
        return sum([payout.amount for payout in payouts])

    def payout_status(self, obj):
        payout_diff = self.seller_price(obj) - self.total_paid_to_seller(obj)
        if payout_diff == 0:
            return format_html("<p>&#128994;</p>")
        elif payout_diff > 0:
            return format_html("<p>&#128993;</p>")
        else:
            return format_html("<p>&#128308;</p>")

    def total_invoiced_from_seller(self, obj):
        seller_invoice_payable_line_items = SellerInvoicePayableLineItem.objects.filter(
            order=obj
        )
        return sum(
            [
                seller_invoice_payable_line_items.amount
                for seller_invoice_payable_line_items in seller_invoice_payable_line_items
            ]
        )

    def seller_invoice_status(self, obj):
        payout_diff = self.total_invoiced_from_seller(obj) - self.total_paid_to_seller(
            obj
        )
        if payout_diff == 0 or self.total_invoiced_from_seller(obj) == 0:
            return format_html("<p>&#128994;</p>")
        elif payout_diff >= 0:
            return format_html("<p>&#128993;</p>")
        else:
            return format_html("<p>&#128308;</p>")


class MainProductWasteTypeAdmin(admin.ModelAdmin):
    model = UserAddress
    search_fields = ["main_product__name", "waste_type__name"]


class SellerInvoicePayableAdmin(admin.ModelAdmin):
    model = SellerInvoicePayable
    list_display = ("seller_location", "supplier_invoice_id", "amount", "status")
    search_fields = ["id", "seller_location__name", "supplier_invoice_id"]
    inlines = [
        SellerInvoicePayableLineItemInline,
    ]


class SellerInvoicePayableLineItemAdmin(admin.ModelAdmin):
    model = SellerInvoicePayableLineItem
    search_fields = ["id", "seller_invoice_payable__id", "order__id"]


class PayoutAdmin(admin.ModelAdmin):
    model = Payout
    search_fields = ["id", "melio_payout_id", "stripe_transfer_id"]


# Register your models here.
admin.site.register(Seller, SellerAdmin)
admin.site.register(SellerLocation, SellerLocationAdmin)
admin.site.register(SellerProduct, SellerProductAdmin)
admin.site.register(SellerProductSellerLocation, SellerProductSellerLocationAdmin)
admin.site.register(UserAddress, UserAddressAdmin)
admin.site.register(UserGroup, UserGroupAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(UserGroupUser)
admin.site.register(UserUserAddress)
admin.site.register(AddOnChoice, AddOnChoiceAdmin)
admin.site.register(AddOn, AddOnAdmin)
admin.site.register(MainProductAddOn)
admin.site.register(MainProductCategory, MainProductCategoryAdmin)
admin.site.register(MainProductCategoryInfo)
admin.site.register(MainProduct, MainProductAdmin)
admin.site.register(MainProductInfo, MainProductInfoAdmin)
admin.site.register(MainProductWasteType, MainProductWasteTypeAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(OrderGroup, OrderGroupAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderLineItemType)
admin.site.register(OrderLineItem)
admin.site.register(ProductAddOnChoice)
admin.site.register(WasteType)
admin.site.register(DisposalLocation)
admin.site.register(DisposalLocationWasteType)
admin.site.register(UserSellerReview)
admin.site.register(UserAddressType)
admin.site.register(OrderDisposalTicket)
admin.site.register(ServiceRecurringFrequency)
admin.site.register(MainProductServiceRecurringFrequency)
admin.site.register(
    SellerProductSellerLocationService, SellerProductSellerLocationServiceAdmin
)
admin.site.register(SellerProductSellerLocationServiceRecurringFrequency)
admin.site.register(SellerProductSellerLocationRental)
admin.site.register(
    SellerProductSellerLocationMaterial, SellerProductSellerLocationMaterialAdmin
)
admin.site.register(SellerProductSellerLocationMaterialWasteType)
admin.site.register(DayOfWeek)
admin.site.register(TimeSlot)
admin.site.register(Subscription)
admin.site.register(Payout, PayoutAdmin)
admin.site.register(SellerInvoicePayable, SellerInvoicePayableAdmin)
admin.site.register(SellerInvoicePayableLineItem, SellerInvoicePayableLineItemAdmin)

# Unregister auth models.
admin.site.unregister(DjangoUser)
admin.site.unregister(Group)
