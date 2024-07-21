import csv

from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path

from api.admin.filters.seller_product_seller_location_seller.rental_mode_filter import (
    RentalModeFilter,
)
from api.admin.inlines import (
    SellerProductSellerLocationMaterialInline,
    SellerProductSellerLocationRentalInline,
    SellerProductSellerLocationRentalMultiStepInline,
    SellerProductSellerLocationRentalOneStepInline,
    SellerProductSellerLocationServiceInline,
    SellerProductSellerLocationServiceTimesPerWeekInline,
)
from api.forms import CsvImportForm
from api.models import SellerLocation, SellerProduct, SellerProductSellerLocation
from common.admin.admin.base_admin import BaseModelAdmin


@admin.register(SellerProductSellerLocation)
class SellerProductSellerLocationAdmin(BaseModelAdmin):
    search_fields = [
        "seller_location__name",
        "seller_location__seller__name",
        "seller_product__product__main_product__name",
    ]
    list_display = ("seller_product", "seller_location", "get_seller")
    raw_id_fields = ("created_by", "updated_by")
    autocomplete_fields = ["seller_product", "seller_location"]
    list_filter = (
        "seller_product__product__main_product__main_product_category",
        "seller_location__seller",
        RentalModeFilter,
    )
    inlines = [
        SellerProductSellerLocationRentalOneStepInline,
        SellerProductSellerLocationRentalInline,
        SellerProductSellerLocationRentalMultiStepInline,
        SellerProductSellerLocationServiceInline,
        SellerProductSellerLocationServiceTimesPerWeekInline,
        SellerProductSellerLocationMaterialInline,
    ]
    readonly_fields = BaseModelAdmin.readonly_fields

    @admin.display(description="Seller")
    def get_seller(self, obj):
        return obj.seller_location.seller

    change_list_template = (
        "admin/entities/seller_product_seller_location_changelist.html"
    )

    def change_view(
        self,
        request,
        object_id,
        form_url="",
        extra_context=None,
    ):
        """
        Dynamically change inlines based on the Pricing Model configuration
        of the Main Product.
        """
        obj = self.model.objects.filter(pk=object_id).first()

        # Begin with no inlines and add them based on the Pricing Model.
        self.inlines = []

        if obj:
            main_product = obj.seller_product.product.main_product
            if main_product.has_rental_one_step:
                self.inlines += [SellerProductSellerLocationRentalOneStepInline]
            if main_product.has_rental:
                # Represents the "RentalTwoStep" pricing model.
                self.inlines += [SellerProductSellerLocationRentalInline]
            if main_product.has_rental_multi_step:
                self.inlines += [SellerProductSellerLocationRentalMultiStepInline]
            if main_product.has_service:
                self.inlines += [SellerProductSellerLocationServiceInline]
            if main_product.has_service_times_per_week:
                self.inlines += [SellerProductSellerLocationServiceTimesPerWeekInline]
            if main_product.has_material:
                self.inlines += [SellerProductSellerLocationMaterialInline]

        return super().change_view(
            request,
            object_id,
            form_url=form_url,
            extra_context=extra_context,
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
