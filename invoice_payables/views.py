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
    context["invoice_payable"] = seller_invoice_payable
    line_items = SellerInvoicePayableLineItem.objects.filter(seller_invoice_payable = seller_invoice_payable)
    related_orders = Order.objects.filter(
        id__in=line_items.values_list('order_id', flat=True)
    )
    context["related_orders"] = related_orders
    return render(request, 'invoice_payables/invoice_detail.html', context)