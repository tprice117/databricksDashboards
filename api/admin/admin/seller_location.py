import csv

from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path
from django.utils.html import format_html

from api.admin.filters.seller_location.admin_tasks import SellerLocationAdminTasksFilter
from api.admin.inlines import (
    SellerLocationMailingAddressInline,
    SellerProductSellerLocationInline,
)
from api.forms import CsvImportForm
from api.models import (
    OrderLineItem,
    Payout,
    Seller,
    SellerInvoicePayableLineItem,
    SellerLocation,
)


@admin.register(SellerLocation)
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
    list_filter = [
        SellerLocationAdminTasksFilter,
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
                "id",
                "seller_id",
                "name",
                "street",
                "city",
                "state",
                "postal_code",
                "country",
                "stripe_connect_account_id",
                "order_email",
            ]
            for row in reader:
                print(row.keys())
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(
                        request,
                        "Your csv file must have a header rows with 'seller_id', 'name', 'street', 'city', 'state', 'postal_code', 'country', 'stripe_connect_account_id', and 'order_email' as the first columns.",
                    )
                    return redirect("..")

            # Create User Groups.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                print(row)
                if row.get("id", None) is not None:
                    seller = SellerLocation.objects.get(id=row["id"])
                    if row["name"].strip() != "":
                        seller.name = row["name"]
                    if row["street"].strip() != "":
                        seller.street = row["street"]
                    if row["city"].strip() != "":
                        seller.city = row["city"]
                    if row["state"].strip() != "":
                        seller.state = row["state"]
                    if row["postal_code"].strip() != "":
                        seller.postal_code = row["postal_code"]
                    if row["country"].strip() != "":
                        seller.country = row["country"]
                    if row["stripe_connect_account_id"].strip() != "":
                        seller.stripe_connect_account_id = row[
                            "stripe_connect_account_id"
                        ]
                    if row["order_email"].strip() != "":
                        seller.order_email = row["order_email"]
                    seller.save()
                elif SellerLocation.objects.filter(name=row["name"]).count() == 0:
                    test, test2 = SellerLocation.objects.get_or_create(
                        seller=Seller.objects.get(id=row["seller_id"]),
                        name=row["name"],
                        street=row["street"],
                        city=row["city"],
                        state=row["state"],
                        postal_code=row["postal_code"],
                        country=row["country"],
                        stripe_connect_account_id=row["stripe_connect_account_id"],
                        order_email=row["order_email"],
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
