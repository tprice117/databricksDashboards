from django.shortcuts import render, get_object_or_404, redirect
from api.models import *
from django.db.models import F
import logging
from .forms import *
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
    
    # Requery the data
    queryset = (
        Order.objects.filter(seller_invoice_payable_line_items__in=line_items)
        .select_related(
            "order_group__user_address", 
            "order_group__sellerproductsellerlocation__seller_product__product",
        )
        .annotate(
            # seller_invoice_payable_line_items_id=F("seller_invoice_payable_line_items__id"),
            # orderlineitemtype_id=F("order_line_items__order_line_item_type_id"),
            service_address=F("order_group__user_address__name"),
            line_item_type=F("order_line_items__order_line_item_type__name"),
            product_name=F("order_group__seller_product_seller_location__seller_product__product__main_product__name"),
            backbill=F("order_line_items__backbill"),
            rate=F("order_line_items__rate"),
            quantity=F("order_line_items__quantity"),
            order_date=F("start_date"),
        )
        .values(
            "id",
            # "seller_invoice_payable_line_items_id",
            # "orderlineitemtype_id",
            "service_address",
            "line_item_type",
            "product_name",
            "backbill",
            "order_date",
            "rate",
            "quantity",
        )
    )

    if request.method == "POST":
        form_prefix = request.POST.get('form_prefix')
        form = InvoiceLineItemForm(request.POST, prefix=form_prefix)
        if form.is_valid():
            orderlineitem_id = form.cleaned_data["orderlineitem_id"]
            # seller_invoice_payable_line_items_id = form.cleaned_data["seller_invoice_payable_line_items_id"]
            orderlineitem_obj = Order.objects.get(pk=orderlineitem_id)
            seller_invoice_payable_line_item_obj = SellerInvoicePayableLineItem.objects.get(pk=orderlineitem_id)
            # orderlineitemtype_id = OrderLineItem.objects.get(pk=orderlineitem_id)
            orderlineitem_obj.product_name = form.cleaned_data["productName"]
            orderlineitem_obj.service_address = form.cleaned_data["serviceAddress"]
            orderlineitem_obj.line_item_type = form.cleaned_data["lineItemType"]
            orderlineitem_obj.backbill = form.cleaned_data["backbill"]
            orderlineitem_obj.order_date = form.cleaned_data["orderDate"]
            orderlineitem_obj.rate = form.cleaned_data["orderRate"]
            orderlineitem_obj.quantity = form.cleaned_data["orderQuantity"]
            orderlineitem_obj.save()
            seller_invoice_payable_line_item_obj.save()
            print(f"Updated order line item {orderlineitem_id}")
        else:
            print(f"Form is not valid: {form.errors}")
        return redirect('invoice_detail', id=id)  
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
    context["forms"] = [InvoiceLineItemForm(initial={
        "orderlineitem_id": orderlineitem["id"],
        # "seller_invoice_payable_line_items_id": orderlineitem["seller_invoice_payable_line_items_id"],
        # "orderlineitemtype_id": orderlineitem["orderlineitemtype_id"],
        "productName": orderlineitem["product_name"],
        "serviceAddress": orderlineitem["service_address"],
        "lineItemType": orderlineitem["line_item_type"],
        "backbill": orderlineitem["backbill"],
        "orderDate": orderlineitem["order_date"],
        "orderRate": orderlineitem["rate"],
        "orderQuantity": orderlineitem["quantity"],
    }, prefix=str(orderlineitem["id"])) for orderlineitem in queryset]

    context["queryset"] = queryset
    return render(request, "invoice_payables/invoice_detail.html", context)
