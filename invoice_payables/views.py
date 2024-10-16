from django.shortcuts import render, get_object_or_404
from api.models import *
from django.db.models import F
import logging
logger = logging.getLogger(__name__)

# Create your views here.
def index(request):
    context = {}
    invoice_payables_all = SellerInvoicePayable.objects.all()
    context["invoice_payables_all"] = invoice_payables_all
    context["test"] = "test"
    return render(request, "invoice_payables/index.html", context)


def invoice_detail(request, id):
    context = {}
    seller_invoice_payable = SellerInvoicePayable.objects.get(pk=id)
    
    line_items = SellerInvoicePayableLineItem.objects.filter(
        seller_invoice_payable=seller_invoice_payable
    )
    
    if request.method == 'POST':
        # iterate each line item to update the fields using their id as a key
        for line_item in line_items:
            # fetch data using line_item.id as the key in POST data
            line_item.product_name = request.POST.get(f'product_name_{line_item.id}')
            line_item.service_address = request.POST.get(f'service_address_{line_item.id}')
            line_item.line_item_type = request.POST.get(f'line_item_type_{line_item.id}')
            line_item.backbill = bool(request.POST.get(f'backbill_{line_item.id}'))
            print(line_item.backbill)
            line_item.order_date = request.POST.get(f'order_date_{line_item.id}')
            line_item.rate = float(request.POST.get(f'order_rate_{line_item.id}', 0))
            line_item.quantity = float(request.POST.get(f'quantity_{line_item.id}', 0))
            line_item.save()  # Save each updated line item to the database
        context["message"] = "Invoice Line Items Updated Successfully"
        logger.debug(request.POST)

    # Requery the data
    queryset = (
        Order.objects.filter(seller_invoice_payable_line_items__in=line_items)
        .select_related(
            "order_group__user_address", 
            "order_group__sellerproductsellerlocation__seller_product__product",
        )
        .annotate(
            service_address=F("order_group__user_address__name"),
            line_item_type=F("order_line_items__order_line_item_type__name"),
            product_name=F("order_group__seller_product_seller_location__seller_product__product__main_product__name"),
            backbill=F("order_line_items__backbill"),
            rate=F("order_line_items__rate"),
            quantity=F("order_line_items__quantity"),
            order_date=F("start_date"),
        )
        .values(
            "service_address",
            "line_item_type",
            "product_name",
            "backbill",
            "order_date",
            "rate",
            "quantity",
        )
    )
    # Map line items to their orders for use in the template
    line_item_order_map = {item: item.order for item in line_items}

    # Main product query based on the seller location from SellerInvoicePayable
    seller_product_locations = SellerProductSellerLocation.objects.filter(
        seller_location=seller_invoice_payable.seller_location
    ).select_related("seller_product__product")

    # Get main product from the seller_product_locations
    main_product = None
    for location in seller_product_locations:
        main_product = location.seller_product.product.main_product

    # Context Hash Map
    context["seller_product_locations"] = seller_product_locations
    context["main_product"] = main_product
    context["invoice_payable"] = seller_invoice_payable
    context["line_items"] = line_items
    context["related_orders"] = queryset
    context["line_item_order_map"] = line_item_order_map

    context["queryset"] = queryset
    return render(request, "invoice_payables/invoice_detail.html", context)
