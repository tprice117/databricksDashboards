import csv

from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path
from django.http import HttpResponseRedirect
from import_export.admin import ExportActionMixin
from import_export import resources

from api.admin.filters.seller.admin_tasks import SellerAdminTasksFilter
from api.admin.inlines import SellerLocationInline, SellerProductInline
from api.forms import CsvImportForm
from api.models import Seller
from common.admin.admin.base_admin import BaseModelAdmin


class SellerResource(resources.ModelResource):
    class Meta:
        model = Seller
        skip_unchanged = True


@admin.register(Seller)
class SellerAdmin(BaseModelAdmin, ExportActionMixin):
    resource_classes = [SellerResource]
    # Add dropdown to see seller dashboard.
    actions = ["view_seller_dashboard"]

    def view_seller_dashboard(self, request, queryset):
        for seller in queryset:
            return HttpResponseRedirect(seller.dashboard_url)

    search_fields = [
        "name",
    ]
    inlines = [
        SellerProductInline,
        SellerLocationInline,
    ]
    list_filter = [
        SellerAdminTasksFilter,
    ]
    raw_id_fields = ("created_by", "updated_by")

    import_export_change_list_template = "admin/entities/seller_changelist.html"

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
