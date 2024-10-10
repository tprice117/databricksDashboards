from django.shortcuts import render, get_object_or_404
from api.models import *
from django.db.models import F

# Create your views here.
def index(request):
    context = {}
    invoice_payables_all = SellerInvoicePayable.objects.all()
    context["invoice_payables_all"] = invoice_payables_all
    context["test"] = "test"
    return render(request, "invoice_payables/index.html", context)

def invoice_detail(request, id):
    context = {}
    # Get the specific SellerInvoicePayable object by the UUID (assuming 'id' is a UUIDField)
    seller_invoice_payable = SellerInvoicePayable.objects.get(pk=id)

    # Fetch all related SellerInvoicePayableLineItem objects for the given SellerInvoicePayable UUID
    line_items = SellerInvoicePayableLineItem.objects.filter(
        seller_invoice_payable=seller_invoice_payable  # Filter line items by the specific UUID
    )
    # Now filter the Order objects by matching the related SellerInvoicePayableLineItem objects
    queryset = Order.objects.filter(
        seller_invoice_payable_line_items__in=line_items  # Use the reverse relationship to filter
    ).select_related(
        'order_group__user_address',  # For service address from OrderGroup -> UserAddress
        'order_group__sellerproductsellerlocation__seller_product__product',  # For product name
    ).prefetch_related(
        'order_line_items_set__orderlineitemtype',  # For type from OrderLineItemType
    ).annotate(
        service_address=F('order_group__user_address__name'),  # UserAddress.name
        backbill=F('order_line_items__backbill'),  # OrderLineItem.backbill
        rate=F('order_line_items__rate'),  # OrderLineItem.rate
        quantity=F('order_line_items__quantity'),  # OrderLineItem.quantity
        order_date=F('start_date'),  # Order.start_date
    ).values(
        'service_address',  # userAddress.name
        'backbill',  # OrderLineItem backbill
        'order_date',  # Order start_date
        'rate',  # OrderLineItem rate
        'quantity'  # OrderLineItem quantity
    )

    # Map line items to their corresponding orders for use in the template
    line_item_order_map = {item: item.order for item in line_items}

    # Main product query based on the seller location from SellerInvoicePayable
    seller_product_locations = SellerProductSellerLocation.objects.filter(
        seller_location=seller_invoice_payable.seller_location
    ).select_related('seller_product__product')

    # Get the main product from the seller_product_locations
    main_product = None
    for location in seller_product_locations:
        main_product = location.seller_product.product.main_product

    # Add necessary context for rendering the template
    context["seller_product_locations"] = seller_product_locations
    context["main_product"] = main_product
    context["invoice_payable"] = seller_invoice_payable
    context["line_items"] = line_items
    context["related_orders"] = queryset  # Pass the filtered queryset here
    context["line_item_order_map"] = line_item_order_map

    context["queryset"] = queryset
    return render(request, 'invoice_payables/invoice_detail.html', context)