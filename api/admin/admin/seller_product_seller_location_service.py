import csv
import logging

from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path

from api.admin.inlines import SellerProductSellerLocationServiceRecurringFrequencyInline
from api.forms import CsvImportForm
from api.models import SellerProductSellerLocation, SellerProductSellerLocationService

logger = logging.getLogger(__name__)


@admin.register(SellerProductSellerLocationService)
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
                        # Create SellerProductSellerLocationService.
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
                    logger.error(
                        f"SellerProductSellerLocationServiceAdmin.import_csv: [{ex}]",
                        exc_info=ex,
                    )

            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)
