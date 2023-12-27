import csv

from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path

from api.forms import CsvImportForm
from api.models import Product, Seller, SellerProduct


@admin.register(SellerProduct)
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
