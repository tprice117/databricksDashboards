from django.contrib import admin
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
    fields = ('order_line_item_type', 'rate', 'quantity', 'downstream_price', 'platform_fee_percent', 'seller_payout_price')
    readonly_fields = ('downstream_price', 'seller_payout_price')
    show_change_link = True
    extra=0

    def downstream_price(self, obj):
        return round((obj.rate or 0) * (obj.quantity or 0), 2)
    
    def seller_payout_price(self, obj):
        total_price = self.downstream_price(obj)
        application_fee = total_price * (obj.platform_fee_percent / 100)
        return round(total_price - application_fee, 2)

class OrderDisposalTicketInline(admin.TabularInline):
    model = OrderDisposalTicket
    fields = ('ticket_id', 'disposal_location', 'waste_type', 'weight')
    show_change_link = True
    extra=0

class PayoutLineItemInlineForm(forms.ModelForm):
    model = PayoutLineItem

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(self)
        if self.instance and self.instance.amount:
            for f in self.fields:
                self.fields[f].disabled = True

class PayoutLineItemInline(admin.TabularInline):
    model = PayoutLineItem
    form = PayoutLineItemInlineForm
    fields = ('order', 'amount', 'description')
    autocomplete_fields = ["order",]
    show_change_link = True
    extra=0
    can_delete = False

    def has_add_permission(self, request, obj):
        # Only show add button if Payout is new.
        return not obj
    
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
    show_change_link = True
    extra=0






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

class SellerLocationAdmin(admin.ModelAdmin):
    search_fields = ["name", "seller__name"]
    list_display = ('name', 'seller', 'total_seller_payout_price', 'total_paid_to_seller', 'payout_status', 'total_invoiced_from_seller', 'seller_invoice_status')
    inlines = [
        SellerProductSellerLocationInline,
    ]

    def get_form(self, request, obj=None, **kwargs):
        # just save obj reference for future processing in Inline
        request._obj_ = obj
        return super(SellerLocationAdmin, self).get_form(request, obj, **kwargs)
    
    def total_seller_payout_price(self, obj):
        order_line_items = OrderLineItem.objects.filter(order__order_group__seller_product_seller_location__seller_location=obj)
        return round(sum([order_line_item.rate * order_line_item.quantity * (1 - (order_line_item.platform_fee_percent / 100)) for order_line_item in order_line_items]), 2)

    def total_paid_to_seller(self, obj):
        payout_line_items = PayoutLineItem.objects.filter(order__order_group__seller_product_seller_location__seller_location=obj)
        return sum([payout_line_items.amount  for payout_line_items in payout_line_items])

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
    
class SellerProductAdmin(admin.ModelAdmin):
    search_fields = ["product__product_code", "seller__name"]
    list_display = ('product', 'seller')
    list_filter = ('product__main_product__main_product_category', 'seller')

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

class SellerProductSellerLocationServiceAdmin(admin.ModelAdmin):
    inlines = [
        SellerProductSellerLocationServiceRecurringFrequencyInline,
    ]

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

class UserGroupAdmin(admin.ModelAdmin):
    model = UserGroup
    search_fields = ["name"]
    inlines = [
        UserInline,
    ]

class OrderGroupAdmin(admin.ModelAdmin):
    model = OrderGroup
    list_display = ('user', 'user_address', 'seller_product_seller_location')
    list_filter = (CreatedDateFilter,)
    autocomplete_fields = ["seller_product_seller_location",]
    inlines = [
        SubscriptionInline,
        OrderInline,
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
    ]

    def customer_price(self, obj):
        return round(obj.customer_price(), 2)
    
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
    
    def seller_price(self, obj):
        return round(obj.seller_price(), 2)

    def total_paid_to_seller(self, obj):
        payout_line_items = PayoutLineItem.objects.filter(order=obj)
        return sum([payout_line_items.amount  for payout_line_items in payout_line_items])

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
        if payout_diff == 0:
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
    inlines = [
        SellerInvoicePayableLineItemInline,
    ]

class SellerInvoicePayableLineItemAdmin(admin.ModelAdmin):
    model = SellerInvoicePayableLineItem

class PayoutLineItemAdmin(admin.ModelAdmin):
    model = PayoutLineItem
    search_fields = ["id", "payout__id", "order__id"]
    autocomplete_fields = ["order",]
    # filter_horizontal = ('orders',)

class PayoutAdmin(admin.ModelAdmin):
    model = Payout
    list_display = ('seller_location', 'total_amount',)
    search_fields = ["id","melio_payout_id", "stripe_transfer_id", "total_amount"]
    readonly_fields = ('melio_payout_id', 'stripe_transfer_id', 'total_amount',)
    inlines = [
        PayoutLineItemInline,
    ]

    def save_formset(self, request, form, formset, change):
        # Get payout model.
        payout = form.save(commit=False)
        
        # Check that all PayoutLineItems are for the same SellerLocation.
        payout_line_items = formset.save(commit=False)
        seller_location = None
        for payout_line_item in payout_line_items:
            if seller_location is None:
                seller_location = payout_line_item.order.order_group.seller_product_seller_location.seller_location
            elif seller_location != payout_line_item.order.order_group.seller_product_seller_location.seller_location:
                raise Exception('PayoutLineItems must be for the same Seller Location.')

        # If all from same SellerLocation, compute total amount.
        total_amount = sum([payout_line_item.amount for payout_line_item in payout_line_items])

        # Payout via Melio or Stripe.
        # if seller_location.seller.melio_account_id:
        #     # Payout via Melio.
        #     melio_payout_id = melio_payout(payout_line_items, seller_location.seller.melio_account_id, total_amount)
        #     payout.melio_payout_id = melio_payout_id
        # else:
        # Payout via Stripe.
        transfer = stripe.Transfer.create(
            amount=round(total_amount * 100),
            currency="usd",
            destination=seller_location.stripe_connect_account_id,
            transfer_group=payout.id,
        )
        payout.stripe_transfer_id = transfer.id

        payout.save()
        for payout_line_item in payout_line_items:
            payout_line_item.save()
        formset.save_m2m()

    def seller_location(self, obj):
        payout_line_items = PayoutLineItem.objects.filter(payout=obj)
        return payout_line_items[0].order.order_group.seller_product_seller_location.seller_location
    
    def total_amount(self, obj):
        payout_line_items = PayoutLineItem.objects.filter(payout=obj)
        return round(sum([payout_line_items.amount  for payout_line_items in payout_line_items]), 2)
        
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
admin.site.register(PayoutLineItem, PayoutLineItemAdmin)
admin.site.register(Payout, PayoutAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(PaymentLineItem, PaymentLineItemAdmin)
admin.site.register(SellerInvoicePayable, SellerInvoicePayableAdmin)
admin.site.register(SellerInvoicePayableLineItem, SellerInvoicePayableLineItemAdmin)

# Unregister auth models.
admin.site.unregister(DjangoUser)
admin.site.unregister(Group)
