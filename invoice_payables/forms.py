import datetime

from django import forms
from django.core.exceptions import ValidationError
from api.models import *

class InvoiceLineItemForm(forms.Form):
    orderlineitem_id = forms.CharField(max_length=255, widget=forms.TextInput(attrs={"class": "form-control"}))

    # seller_invoice_payable_line_items_id = forms.CharField(max_length=255, widget=forms.TextInput(attrs={"class": "form-control"}))
    # orderlineitemtype_id = forms.CharField(max_length=255, widget=forms.TextInput(attrs={"class": "form-control"}))
    
    productName= forms.CharField( max_length=255, widget=forms.TextInput(attrs={"class": "form-control"}))
    serviceAddress = forms.CharField( max_length=255, widget=forms.TextInput(attrs={"class": "form-control"}))
    lineItemType = forms.CharField( max_length=255, widget=forms.TextInput(attrs={"class": "form-control"}))
    backbill = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={"class": "form-control"}))
    orderDate = forms.DateField( widget=forms.DateInput(attrs={"class": "form-control"}))
    orderRate = forms.DecimalField( widget=forms.NumberInput(attrs={"class": "form-control"}))
    orderQuantity = forms.DecimalField( widget=forms.NumberInput(attrs={"class": "form-control"}))

    