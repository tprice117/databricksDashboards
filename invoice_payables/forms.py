import datetime

from django import forms
from django.core.exceptions import ValidationError
from api.models import *


class InvoiceLineItemForm(forms.Form):
    orderlineitem_id = forms.CharField(
        max_length=255, required=False, widget=forms.TextInput(attrs={"class": "form-control"})
    )
    productName = forms.CharField(
        max_length=255, required=False, widget=forms.TextInput(attrs={"class": "form-control"})
    )
    serviceAddress = forms.CharField(
        max_length=255, required=False,  widget=forms.TextInput(attrs={"class": "form-control"})
    )
    lineItemType = forms.CharField(
        max_length=255, required=False,  widget=forms.TextInput(attrs={"class": "form-control"})
    )
    backbill = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={"class": "form-control"})
    )
    orderDate = forms.DateField(required=False, widget=forms.DateInput(attrs={"class": "form-control"}))
    orderRate = forms.DecimalField(
        required=False, widget=forms.NumberInput(attrs={"class": "form-control"})
    )
    orderQuantity = forms.DecimalField(
        required=False, widget=forms.NumberInput(attrs={"class": "form-control"})
    )
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
    def save(self):
        data = self.cleaned_data
        orderlineitem_id = data.get('orderlineitem_id')

        # Fetch or create the OrderLineItem instance
        orderlineitem, created = OrderLineItem.objects.update_or_create(
            id=orderlineitem_id,
            defaults={
                'product_name': data.get('productName'),
                'service_address': data.get('serviceAddress'),
                'line_item_type': data.get('lineItemType'),
                'backbill': data.get('backbill'),
                'order_date': data.get('orderDate'),
                'rate': data.get('orderRate'),
                'quantity': data.get('orderQuantity'),
                'updated_by': self.user,  # Assign the current user
            }
        )
        return orderlineitem