import csv
import logging

from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path
from import_export.admin import ExportActionMixin
from import_export import resources

from api.forms import CsvImportForm
from api.models import SellerProductSellerLocationMaterialWasteType
from api.models.main_product.main_product_waste_type import MainProductWasteType
from api.models.seller.seller_product_seller_location_material import (
    SellerProductSellerLocationMaterial,
)
from common.admin.admin.base_admin import BaseModelAdmin

logger = logging.getLogger(__name__)


class SellerProductSellerLocationMaterialWasteTypeResource(resources.ModelResource):
    class Meta:
        model = SellerProductSellerLocationMaterialWasteType
        skip_unchanged = True


@admin.register(SellerProductSellerLocationMaterialWasteType)
class SellerProductSellerLocationMaterialWasteTypeAdmin(
    BaseModelAdmin, ExportActionMixin
):
    resource_classes = [SellerProductSellerLocationMaterialWasteTypeResource]
    import_export_change_list_template = "admin/entities/seller_product_seller_location_material_waste_type_changelist.html"

    raw_id_fields = (
        "seller_product_seller_location_material",
        "created_by",
        "updated_by",
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
                "seller_product_seller_location_material_id",
                "main_product_waste_type_id",
                "price_per_ton",
                "tonnage_included",
            ]
            for row in reader:
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(
                        request,
                        "Your csv file must have a header rows with 'seller_product_seller_location_material_id', 'main_product_waste_type_id', 'price_per_ton', and 'tonnage_included' as the first column.",
                    )
                    return redirect("..")

            # Create SellerProduct.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                try:
                    seller_product_seller_location_material = (
                        SellerProductSellerLocationMaterial.objects.get(
                            id=row["seller_product_seller_location_material_id"]
                        )
                    )
                    does_exist = (
                        SellerProductSellerLocationMaterialWasteType.objects.filter(
                            seller_product_seller_location_material=seller_product_seller_location_material,
                            main_product_waste_type=MainProductWasteType.objects.get(
                                id=row["main_product_waste_type_id"],
                            ),
                        ).count()
                        > 0
                    )

                    if not does_exist:
                        # Create SellerProductSellerLocation.
                        (
                            test,
                            test2,
                        ) = SellerProductSellerLocationMaterialWasteType.objects.get_or_create(
                            seller_product_seller_location_material=SellerProductSellerLocationMaterial.objects.get(
                                id=row["seller_product_seller_location_material_id"],
                            ),
                            main_product_waste_type=MainProductWasteType.objects.get(
                                id=row["main_product_waste_type_id"],
                            ),
                            price_per_ton=row["price_per_ton"],
                            tonnage_included=row["tonnage_included"],
                        )
                    else:
                        material_waste_type = SellerProductSellerLocationMaterialWasteType.objects.get(
                            seller_product_seller_location_material=seller_product_seller_location_material,
                            main_product_waste_type=MainProductWasteType.objects.get(
                                id=row["main_product_waste_type_id"],
                            ),
                        )
                        material_waste_type.price_per_ton = row["price_per_ton"]
                        material_waste_type.tonnage_included = row["tonnage_included"]
                        material_waste_type.save()
                except Exception as ex:
                    print("Error: " + str(ex))
                    logger.error(
                        f"SellerProductSellerLocationMaterialWasteTypeAdmin.import_csv: [{ex}]",
                        exc_info=ex,
                    )

            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(request, "admin/csv_form.html", payload)
