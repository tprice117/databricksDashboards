import csv
from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path
import requests
from .models import *
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.models import User as DjangoUser
from django.contrib.auth.models import Group
from .forms import *
import stripe
from django.utils.html import format_html
from django.contrib import admin, messages

stripe.api_key = settings.STRIPE_SECRET_KEY

# Filters.
class CreatedDateFilter(SimpleListFilter):
    title = 'Creation Date' # or use _('country') for translated title
    parameter_name = 'created_on'

    def lookups(self, request, model_admin):
        return [
            ("today", "Today"),
            ("yesterday", "Yesterday"),
            ("7d", "Last 7 Days"),
            ("1m", "This Month"),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'Today':
            return queryset.filter(created_on__date=datetime.date.today())  
        elif self.value() == 'Yesterday':
            return queryset.filter(created_on__date=datetime.date.today() - datetime.timedelta(days=1))
        elif self.value() == 'Last 7 Days':
            return queryset.filter(created_on__date__gte=datetime.date.today() - datetime.timedelta(days=7))
        elif self.value() == 'This Month':
            return queryset.filter(created_on__date__gte=datetime.date.today().replace(day=1))


# Inlines.
class AddOnChoiceInline(admin.TabularInline):
    model = AddOnChoice
    fields = ('name',)
    show_change_link = True
    extra=0

class MainProductCategoryInfoInline(admin.TabularInline):
    model = MainProductCategoryInfo
    fields = ('name',)
    show_change_link = True
    extra=0

class MainProductInline(admin.TabularInline):
    model = MainProduct
    fields = ('name',)
    show_change_link = True
    extra=0

class MainProductInfoInline(admin.TabularInline):
    model = MainProductInfo
    fields = ('name',)
    show_change_link = True
    extra=0

class OrderGroupServiceInline(admin.TabularInline):
    model = OrderGroupService
    fields = ('rate', 'miles')
    show_change_link = True
    extra=0

class OrderGroupRentalInline(admin.TabularInline):
    model = OrderGroupRental
    fields = ('included_days', 'price_per_day_included', 'price_per_day_additional')
    show_change_link = True
    extra=0

class OrderGroupMaterialInline(admin.TabularInline):
    model = OrderGroupMaterial
    fields = ('price_per_ton', 'tonnage_included')
    show_change_link = True
    extra=0

class OrderInline(admin.TabularInline):
    model = Order
    fields = ('start_date', 'end_date', 'service_date', 'submitted_on')
    show_change_link = True
    extra=0

class SubscriptionInline(admin.StackedInline):
    model = Subscription
    fields = ('frequency', 'service_day')
    show_change_link = True
    extra=0

class ProductInline(admin.TabularInline):
    model = Product
    fields = ('product_code', 'description')
    show_change_link = True
    extra=0

class ProductAddOnChoiceInline(admin.TabularInline):
    model = ProductAddOnChoice
    fields = ('name', 'product', 'add_on_choice')
    show_change_link = True
    extra=0

class SellerLocationInline(admin.TabularInline):
    model = SellerLocation
    fields = ('name',)
    show_change_link = True
    extra=0

class SellerLocationMailingAddressInline(admin.TabularInline):
    model = SellerLocationMailingAddress
    fields = ('street', 'city', 'state', 'postal_code', 'country')
    show_change_link = True
    extra=0

class SellerProductInline(admin.TabularInline):
    model = SellerProduct
    fields = ('product',)
    show_change_link = True
    extra=0

class SellerProductSellerLocationInline(admin.TabularInline):
    model = SellerProductSellerLocation
    fields = ('seller_product', 'total_inventory')
    show_change_link = True
    extra=0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super(SellerProductSellerLocationInline, self).formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'seller_product':
            if request._obj_ is not None:
                print(request._obj_)
                print(field.queryset)
                field.queryset = field.queryset.filter(seller = request._obj_.seller)  
            else:
                field.queryset = field.queryset.none()
        return field
    
class SellerProductSellerLocationServiceInline(admin.StackedInline):
    model = SellerProductSellerLocationService
    show_change_link = True
    extra=0

class SellerProductSellerLocationServiceRecurringFrequencyInline(admin.StackedInline):
    model = SellerProductSellerLocationServiceRecurringFrequency
    show_change_link = True
    extra=0

class SellerProductSellerLocationRentalInline(admin.StackedInline):
    model = SellerProductSellerLocationRental
    show_change_link = True
    extra=0

class SellerProductSellerLocationMaterialInline(admin.StackedInline):
    model = SellerProductSellerLocationMaterial
    show_change_link = True
    extra=0

class SellerProductSellerLocationMaterialWasteTypeInline(admin.StackedInline):
    model = SellerProductSellerLocationMaterialWasteType
    show_change_link = True
    extra=0
    
class UserGroupUserInline(admin.TabularInline):
    model = UserGroupUser
    fields = ('user_group', 'user')
    show_change_link = True
    extra=0

class UserInline(admin.TabularInline):
    model = User
    fields = ('is_admin', 'first_name', 'last_name', 'email', 'phone',)
    readonly_fields = ('first_name', 'last_name', 'email', 'phone')
    show_change_link = True
    extra=0

class OrderLineItemInline(admin.TabularInline):
    model = OrderLineItem
    fields = ('order_line_item_type', 'rate', 'quantity', 'seller_payout_price', 'platform_fee_percent','downstream_price',)
    readonly_fields = ('downstream_price', 'seller_payout_price')
    show_change_link = True
    extra=0

    def seller_payout_price(self, obj):
        return round((obj.rate or 0) * (obj.quantity or 0), 2)
    
    def downstream_price(self, obj):
        seller_price = self.seller_payout_price(obj)
        customer_price = seller_price * (1 + (obj.platform_fee_percent / 100))
        return round(customer_price, 2)

class OrderDisposalTicketInline(admin.TabularInline):
    model = OrderDisposalTicket
    fields = ('ticket_id', 'disposal_location', 'waste_type', 'weight')
    show_change_link = True
    extra=0

class PayoutInline(admin.TabularInline):
    model = Payout
    fields = ('amount', 'description', 'stripe_transfer_id', 'melio_payout_id')
    show_change_link = True
    extra=0
    can_delete = False
    
class PaymentLineItemInline(admin.TabularInline):
    model = PaymentLineItem
    readonly_fields = ('order', 'invoiced', 'paid', 'stripe_invoice_line_item_id',)
    extra=0
    can_delete = False

    def invoiced(self, obj):
        invoiced, _ = obj.amount()
        return invoiced
    
    def paid(self, obj):
        _, paid = obj.amount()
        return paid

class SellerInvoicePayableLineItemInline(admin.TabularInline):
    model = SellerInvoicePayableLineItem
    fields = ('order', 'amount', 'description')
    autocomplete_fields = ["order",]
    show_change_link = True
    extra=0

# class SellerInvoicePayableItemReadOnlyInline(admin.TabularInline):
#     model = SellerInvoicePayableLineItem
#     fields = ('amount', 'description')
#     readonly_fields = ('amount', 'description')
#     extra=0

#     def has_add_permission(self, request, obj):
#         return False






class AddOnChoiceAdmin(admin.ModelAdmin):
    search_fields = ["name", "add_on__name"]
    list_display = ('name', 'add_on')

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
    list_display = ('__str__', 'main_product')
    inlines = [
        ProductAddOnChoiceInline,
    ]

class MainProductAdmin(admin.ModelAdmin):
    search_fields = ["name", "main_product_category__name"]
    list_display = ('name', 'main_product_category', 'sort')
    inlines = [
        ProductInline,
        MainProductInfoInline,
    ]

class MainProductInfoAdmin(admin.ModelAdmin):
    search_fields = ["name", "main_product__name"]
    list_display = ('name', 'main_product')
    
class SellerAdmin(admin.ModelAdmin):
    search_fields = ["name",]
    inlines = [
        SellerProductInline,
        SellerLocationInline,
    ]

    change_list_template = "admin/entities/seller_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode('utf-8').splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            keys = ["name", "phone", "website", "type_display", "location_type", "status", "lead_time_hrs", "marketplace_display_name", "location_logo_url", "badge"]
            for row in reader:
                print(row.keys())
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(request, "Your csv file must have a header rows with 'name', 'phone', 'website', 'type_display', 'location_type', 'status', 'lead_time_hrs', 'marketplace_display_name', 'location_logo_url', and 'badge' as the first columns.")
                    return redirect("..")
                
            # Create User Groups.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                print(row)
                if (Seller.objects.filter(name=row['name']).count() == 0):
                    test, test2 = Seller.objects.get_or_create(
                        name=row['name'],
                        phone=row['phone'],
                        website=row['website'],
                        type_display=row['type_display'],
                        location_type=row['location_type'],
                        status=row['status'],
                        lead_time_hrs=row['lead_time_hrs'],
                        marketplace_display_name=row['marketplace_display_name'],
                        location_logo_url=row['location_logo_url'],
                        badge=row['badge'],
                    )
                    print(test)
                    print(test2)
                else:
                    print("USER ALREADY EXISITS: " + row['name'])
            
            
            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/csv_form.html", payload
        )


class SellerLocationAdmin(admin.ModelAdmin):
    search_fields = ["name", "seller__name"]
    list_display = ('name', 'seller', 'total_seller_payout_price', 'total_paid_to_seller', 'payout_status', 'total_invoiced_from_seller', 'seller_invoice_status')
    inlines = [
        SellerLocationMailingAddressInline,
        SellerProductSellerLocationInline,
    ]

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj
        return super(SellerLocationAdmin, self).get_form(request, obj, **kwargs)
    
    def total_paid_to_seller(self, obj):
        payout_line_items = Payout.objects.filter(order__order_group__seller_product_seller_location__seller_location=obj)
        return sum([payout_line_items.amount  for payout_line_items in payout_line_items])

    def total_seller_payout_price(self, obj):
        order_line_items = OrderLineItem.objects.filter(order__order_group__seller_product_seller_location__seller_location=obj)
        return round(sum([order_line_item.rate * order_line_item.quantity for order_line_item in order_line_items]), 2)

    def payout_status(self, obj):
        payout_diff = self.total_seller_payout_price(obj) - self.total_paid_to_seller(obj)
        if payout_diff == 0:
            return format_html("<p>&#128994;</p>")
        elif payout_diff > 0:
            return format_html("<p>&#128993;</p>")
        else:
            return format_html("<p>&#128308;</p>")
        
    def total_invoiced_from_seller(self, obj):
        seller_invoice_payable_line_items = SellerInvoicePayableLineItem.objects.filter(order__order_group__seller_product_seller_location__seller_location=obj)
        return sum([seller_invoice_payable_line_items.amount  for seller_invoice_payable_line_items in seller_invoice_payable_line_items])
    
    def seller_invoice_status(self, obj):
        payout_diff = self.total_invoiced_from_seller(obj) - self.total_paid_to_seller(obj)
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
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode('utf-8').splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            keys = ["seller_id", "name", "street", "city", "state", "postal_code", "country", "stripe_connect_account_id"]
            for row in reader:
                print(row.keys())
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(request, "Your csv file must have a header rows with 'seller_id', 'name', 'street', 'city', 'state', 'postal_code', 'country', and 'stripe_connect_account_id' as the first columns.")
                    return redirect("..")
                
            # Create User Groups.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                print(row)
                if (SellerLocation.objects.filter(name=row['name']).count() == 0):
                    test, test2 = SellerLocation.objects.get_or_create(
                        seller = Seller.objects.get(id=row['seller_id']),
                        name = row['name'],
                        street = row['street'],
                        city = row['city'],
                        state = row['state'],
                        postal_code = row['postal_code'],
                        country = row['country'],
                        stripe_connect_account_id = row['stripe_connect_account_id'],
                    )
                    print(test)
                    print(test2)
                else:
                    print("USER ALREADY EXISITS: " + row['name'])
            
            
            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/csv_form.html", payload
        )
    
class SellerProductAdmin(admin.ModelAdmin):
    search_fields = ["product__product_code", "seller__name"]
    list_display = ('product', 'seller')
    list_filter = ('product__main_product__main_product_category', 'seller')

    change_list_template = "admin/entities/seller_product_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode('utf-8').splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            keys = ["seller_id", "product_id"]
            for row in reader:
                print(row.keys())
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(request, "Your csv file must have a header rows with 'seller_id', 'product_id' as the first columns.")
                    return redirect("..")
                
            # Create SellerProduct.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                print(row)
                does_exist = SellerProduct.objects.filter(
                    seller = Seller.objects.get(id=row['seller_id']),
                    product = Product.objects.get(id=row['product_id']),
                ).count() > 0

                if not does_exist:
                    test, test2 = SellerProduct.objects.get_or_create(
                        seller = Seller.objects.get(id=row['seller_id']),
                        product = Product.objects.get(id=row['product_id']),
                    )
                    print(test)
                    print(test2)
                else:
                    print("SellerProduct ALREADY EXISITS")
            
            
            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/csv_form.html", payload
        )

class SellerProductSellerLocationAdmin(admin.ModelAdmin):
    search_fields = ["seller_location__name", "seller_location__seller__name", "seller_product__product__main_product__name"]
    list_display = ('seller_product', 'seller_location', "get_seller")
    autocomplete_fields = ["seller_product", "seller_location"]
    list_filter = ('seller_product__product__main_product__main_product_category', 'seller_location__seller')
    inlines = [
        SellerProductSellerLocationServiceInline,
        SellerProductSellerLocationRentalInline,
        SellerProductSellerLocationMaterialInline,
    ]

    @admin.display(description='Seller')
    def get_seller(self, obj):
        return obj.seller_location.seller
    
    change_list_template = "admin/entities/seller_product_seller_location_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode('utf-8').splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            keys = ["id", "seller_product_id", "seller_location_id", "total_inventory", "min_price", 'max_price', 'service_radius', 'delivery_fee', 'removal_fee', 'fuel_environmental_markup']
            for row in reader:
                print(row.keys())
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(request, "Your csv file must have a header rows with 'id', 'seller_product_id', 'seller_location_id', 'total_inventory', 'min_price', 'max_price', 'service_radius', 'delivery_fee', 'removal_fee', and 'fuel_environmental_markup' as the first columns.")
                    return redirect("..")
                
            # Create SellerProduct.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                does_exist = SellerProductSellerLocation.objects.filter(
                    seller_product = SellerProduct.objects.get(id=row['seller_product_id']),
                    seller_location = SellerLocation.objects.get(id=row['seller_location_id']),
                ).count() > 0

                if row['id'] == "" and not does_exist:
                    # Create SellerProductSellerLocation.
                    test, test2 = SellerProductSellerLocation.objects.get_or_create(
                        seller_product = SellerProduct.objects.get(id=row['seller_product_id']),
                        seller_location = SellerLocation.objects.get(id=row['seller_location_id']),
                    )
                elif row['id'] != "" and does_exist:
                    seller_product_seller_location = SellerProductSellerLocation.objects.get(id=row['id'])
                    seller_product_seller_location.total_inventory = row['total_inventory']
                    seller_product_seller_location.min_price = row['min_price']
                    seller_product_seller_location.max_price = row['max_price']
                    seller_product_seller_location.service_radius = row['service_radius']
                    seller_product_seller_location.delivery_fee = row['delivery_fee']
                    seller_product_seller_location.removal_fee = row['removal_fee']
                    seller_product_seller_location.fuel_environmental_markup = row['fuel_environmental_markup']
                    seller_product_seller_location.save()
                else:
                    print("SellerProductSellerLocation ALREADY EXISITS")
            
            
            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/csv_form.html", payload
        )

class SellerProductSellerLocationServiceAdmin(admin.ModelAdmin):
    inlines = [
        SellerProductSellerLocationServiceRecurringFrequencyInline,
    ]

    change_list_template = "admin/entities/seller_product_seller_location_service_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode('utf-8').splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            keys = ["seller_product_seller_location_id", 'price_per_mile', 'flat_rate_price']
            for row in reader:
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(request, "Your csv file must have a header rows with 'seller_product_seller_location_id', 'price_per_mile', and 'flat_rate_price' as the first columns.")
                    return redirect("..")
                
            # Create SellerProduct.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                try:
                    seller_product_seller_location = SellerProductSellerLocation.objects.get(id=row['seller_product_seller_location_id'])
                    does_exist = SellerProductSellerLocationService.objects.filter(
                        seller_product_seller_location = seller_product_seller_location,
                    ).count() > 0

                    if not does_exist:
                        # Create SellerProductSellerLocation.
                        test, test2 = SellerProductSellerLocationService.objects.get_or_create(
                            seller_product_seller_location = SellerProductSellerLocation.objects.get(id=row['seller_product_seller_location_id']),
                            price_per_mile = None,
                            flat_rate_price = row['flat_rate_price'],
                        )
                    else:
                        service = SellerProductSellerLocationService.objects.get(
                            seller_product_seller_location = seller_product_seller_location,
                        )
                        service.price_per_mile = None
                        service.flat_rate_price = row['flat_rate_price']
                        service.save()
                except Exception as ex:
                    print("Error: " + str(ex))
            
            
            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/csv_form.html", payload
        )

class SellerProductSellerLocationMaterialAdmin(admin.ModelAdmin):
    inlines = [
        SellerProductSellerLocationMaterialWasteTypeInline,
    ]

class UserAddressAdmin(admin.ModelAdmin):
    model = UserAddress
    list_display = ('name', 'user_group', 'project_id')
    autocomplete_fields = ["user_group", "user"]
    search_fields = ["name", "street"]
    actions = ["create_draft_invoices"]
                
    @admin.action(description="Create Draft Invoices")
    def create_draft_invoices(modeladmin, request, queryset):
        for user_address in queryset:
            # Get all completed orders for this user address.
            completed_orders = Order.objects.filter(
                order_group__user_address=user_address, 
                status=Order.COMPLETE, 
                submitted_on__isnull=False
            )

            # Create draft invoice for any orders that are "undercharged".
            payment = None
            for completed_order in completed_orders:
                payment_line_items = PaymentLineItem.objects.filter(order=completed_order)

                # Compute total amount already invoiced to customer.
                total_invoiced = 0
                for payment_line_item in payment_line_items:
                    invoiced, _ = payment_line_item.amount()
                    total_invoiced += invoiced

                # Compute total amount to be invoiced to customer.
                total_to_be_invoiced = float(completed_order.customer_price()) - float(total_invoiced)

                # Create draft invoice if there is an amount to be invoiced.
                if total_to_be_invoiced > 0:
                    # Create Payment, if None.
                    if not payment:
                        payment = Payment.objects.create(
                            user_address=user_address,
                        )

                    # Create Stripe Invoice Line Item.
                    start_datetime = datetime.datetime.combine(
                        completed_order.start_date, 
                        datetime.datetime.min.time()
                    )
                    end_datetime = datetime.datetime.combine(
                        completed_order.end_date, 
                        datetime.datetime.min.time()
                    )
                    print(start_datetime.timestamp())
                    print(end_datetime.timestamp())
                    
                    stripe_invoice_line_item = stripe.InvoiceItem.create(
                        customer=user_address.stripe_customer_id,
                        description=completed_order.order_group.seller_product_seller_location.seller_product.product.main_product.name + " | " + completed_order.start_date.strftime("%m/%d/%Y") + " - " + completed_order.end_date.strftime("%m/%d/%Y"),
                        amount=round(total_to_be_invoiced * 100),
                        currency="usd",
                        period={
                            "start": round(start_datetime.timestamp()),
                            "end": round(end_datetime.timestamp()),
                        }
                    )

                    # Create PaymentLineItem.
                    PaymentLineItem.objects.create(
                        payment=payment,
                        order=completed_order,
                        stripe_invoice_line_item_id=stripe_invoice_line_item.id,
                    )

            # Create draft invoice for any orders that are "overcharged".
            invoice = stripe.Invoice.create(
                customer=user_address.stripe_customer_id,
            )

            # Update Payment.
            if payment:
                payment.stripe_invoice_id = invoice.id
                payment.save()

            messages.success(request, "Successfully created all needed invoices.")

class UserAdmin(admin.ModelAdmin):
    model = User
    search_fields = ["email", "first_name", "last_name"]
    list_display = ('email', 'first_name', 'last_name', 'cart_orders', 'active_orders')
    autocomplete_fields = ["user_group"]
    list_filter = (CreatedDateFilter, 'user_group')
    inlines = [
        UserGroupUserInline,
    ]

    def cart_orders(self, obj):
        return Order.objects.filter(order_group__user=obj, submitted_on=None).count()
    
    def active_orders(self, obj):
        return Order.objects.filter(order_group__user=obj).exclude(submitted_on=None).count()

    change_list_template = "admin/entities/user_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode('utf-8').splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            keys = ["user_group", "phone", "email", "first_name", "last_name"]
            for row in reader:
                if not all(key in keys for key in list(row.keys())):
                    self.message_user(request, "Your csv file must have a header rows with 'user_group', 'phone', 'email', 'first_name', and 'last_name' as the first columns.")
                    return redirect("..")
                
            # Create User Groups.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                print(row)
                if (User.objects.filter(email=row['email']).count() == 0):
                    test, test2 = User.objects.get_or_create(
                        user_group=UserGroup.objects.get(id=row['user_group']),
                        user_id="",
                        phone = row['phone'],
                        email = row['email'],
                        first_name = row['first_name'],
                        last_name = row['last_name'],
                        is_admin=True,
                    )
                    print(test)
                    print(test2)
                else:
                    print("USER ALREADY EXISITS: " + row['email'])
            
            
            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/csv_form.html", payload
        )

class UserGroupAdmin(admin.ModelAdmin):
    model = UserGroup
    search_fields = ["name"]
    inlines = [
        UserInline,
    ]

    change_list_template = "admin/entities/user_group_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-csv/', self.import_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            csv_file = request.FILES["csv_file"]
            decoded_file = csv_file.read().decode('utf-8').splitlines()

            # Do nothing if first row is not "name".
            reader = csv.DictReader(decoded_file)
            for row in reader:
                if not 'name' in row.keys():
                    self.message_user(request, "Your csv file must have a header row with 'name' as the first column.")
                    return redirect("..")
                
            # Create User Groups.
            reader = csv.DictReader(decoded_file)
            for row in reader:
                print(row)
                test, test2 = UserGroup.objects.get_or_create(
                    name=row['name'],
                )
                print(test)
                print(test2)
            
            self.message_user(request, "Your csv file has been imported")
            return redirect("..")
        form = CsvImportForm()
        payload = {"form": form}
        return render(
            request, "admin/csv_form.html", payload
        )

class OrderGroupAdmin(admin.ModelAdmin):
    model = OrderGroup
    list_display = ('user', 'user_address', 'seller_product_seller_location')
    list_filter = (CreatedDateFilter,)
    autocomplete_fields = ["seller_product_seller_location",]
    inlines = [
        SubscriptionInline,
        OrderInline,
        OrderGroupServiceInline,
        OrderGroupRentalInline,
        OrderGroupMaterialInline,
    ]

class OrderAdmin(admin.ModelAdmin):
    model = Order
    readonly_fields = ('customer_price', 'seller_price',)
    search_fields = ("id",)
    list_display = (
        'order_group', 
        'start_date', 
        'end_date', 
        'status', 
        'service_date', 
        'customer_price', 
        'customer_invoiced',
        'customer_paid',
        'payment_status',
        'seller_price', 
        'total_paid_to_seller', 
        'payout_status', 
        'total_invoiced_from_seller', 
        'seller_invoice_status'
    )
    list_filter = ('status', CreatedDateFilter)
    inlines = [
        OrderLineItemInline,
        OrderDisposalTicketInline,
        PayoutInline,
        SellerInvoicePayableLineItemInline,
    ]
    actions = ["send_payouts"]
                
    @admin.action(description="Send payouts")
    def send_payouts(self, request, queryset):
        for order in queryset:
            # Only send payout if seller has a Stripe Connect Account.
            payout_diff = self.seller_price(order) - self.total_paid_to_seller(order)
            if payout_diff > 0:
                if order.order_group.seller_product_seller_location.seller_location.stripe_connect_account_id:
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
                else:
                    # Payout via Checkbook.
                    url = "https://demo.checkbook.io/v3/check/physical"

                    headers = {
                        "accept": "application/json",
                        "content-type": "application/json"
                    }

                    response = requests.post(url, headers=headers)

        messages.success(request, "Successfully paid out all connected sellers.")

    def customer_price(self, obj):
        return round(obj.customer_price(), 2)
    
    def seller_price(self, obj):
        return round(obj.seller_price(), 2)
    
    def customer_invoiced(self, obj):
        payment_line_items = PaymentLineItem.objects.filter(order=obj)
        total_invoiced = 0
        for payment_line_item in payment_line_items:
            invoiced, paid = payment_line_item.amount()
            total_invoiced += invoiced
        return total_invoiced
    
    def customer_paid(self, obj):
        payment_line_items = PaymentLineItem.objects.filter(order=obj)
        total_paid = 0
        for payment_line_item in payment_line_items:
            invoiced, paid = payment_line_item.amount()
            total_paid += paid
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
        seller_invoice_payable_line_items = SellerInvoicePayableLineItem.objects.filter(order=obj)
        return sum([seller_invoice_payable_line_items.amount  for seller_invoice_payable_line_items in seller_invoice_payable_line_items])
    
    def seller_invoice_status(self, obj):
        payout_diff = self.total_invoiced_from_seller(obj) - self.total_paid_to_seller(obj)
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
    list_display = ('seller_location', 'supplier_invoice_id', 'amount', 'status')
    search_fields = ["id", "seller_location__name", "supplier_invoice_id"]
    inlines = [
        SellerInvoicePayableLineItemInline,
    ]

class SellerInvoicePayableLineItemAdmin(admin.ModelAdmin):
    model = SellerInvoicePayableLineItem
    search_fields = ["id", "seller_invoice_payable__id", "order__id"]

class PayoutAdmin(admin.ModelAdmin):
    model = Payout
    search_fields = ["id","melio_payout_id", "stripe_transfer_id"]
        
class PaymentAdmin(admin.ModelAdmin):
    model = Payment
    list_display = ('user_address', 'total', 'stripe_invoice_id',)
    readonly_fields = ('user_address', 'total', 'stripe_invoice_id',)
    inlines = [
        PaymentLineItemInline,
    ]

    def total(self, obj):
        invoiced, _ = obj.total()
        return invoiced

class PaymentLineItemAdmin(admin.ModelAdmin):
    model = PaymentLineItem
    readonly_fields = ('stripe_invoice_line_item_id', 'payment', 'order')

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
admin.site.register(SellerProductSellerLocationService, SellerProductSellerLocationServiceAdmin)
admin.site.register(SellerProductSellerLocationServiceRecurringFrequency)
admin.site.register(SellerProductSellerLocationRental)
admin.site.register(SellerProductSellerLocationMaterial, SellerProductSellerLocationMaterialAdmin)
admin.site.register(SellerProductSellerLocationMaterialWasteType)
admin.site.register(DayOfWeek)
admin.site.register(TimeSlot)
admin.site.register(Subscription)
admin.site.register(Payout, PayoutAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(PaymentLineItem, PaymentLineItemAdmin)
admin.site.register(SellerInvoicePayable, SellerInvoicePayableAdmin)
admin.site.register(SellerInvoicePayableLineItem, SellerInvoicePayableLineItemAdmin)

# Unregister auth models.
admin.site.unregister(DjangoUser)
admin.site.unregister(Group)
