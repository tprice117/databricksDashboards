from django.shortcuts import render, get_object_or_404
from api.models import *
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
    line_items = SellerInvoicePayableLineItem.objects.filter(seller_invoice_payable = seller_invoice_payable)
    
    related_orders = Order.objects.filter(
        id__in=line_items.values_list('order_id', flat=True)
    )
    line_item_order_map = {item: item.order for item in line_items}
    
    # Main Product query
    seller_invoice_payable = SellerInvoicePayable.objects.get(id=seller_invoice_payable.id)

    seller_product_locations = SellerProductSellerLocation.objects.filter(
        seller_location=seller_invoice_payable.seller_location  # Adjust based on your field names
    ).select_related('seller_product__product')

    for location in seller_product_locations:
        main_product = location.seller_product.product.main_product
    context["seller_product_locations"] = seller_product_locations
    context["main_product"] = main_product


    context["invoice_payable"] = seller_invoice_payable
    context["line_items"] = line_items
    context["related_orders"] = related_orders
    context["line_item_order_map"] = line_item_order_map

    return render(request, 'invoice_payables/invoice_detail.html', context)