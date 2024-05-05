from django import forms
from django.contrib.auth import get_user_model
from api.models import User

from api.models import (
    Order,
    Seller,
    Payout,
    SellerInvoicePayable,
    SellerLocation,
    SellerInvoicePayableLineItem,
)


class UserForm(forms.Form):
    first_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "John"}),
    )
    last_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Doe"}),
    )
    phone = forms.CharField(
        max_length=40,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "(000) 867-5309"}
        ),
    )
    email = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "john.doe@example.com",
                "disabled": True,
            }
        ),
        required=False,
    )
    photo_url = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}), required=False
    )


class SellerForm(forms.Form):
    company_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Awesome Co."}
        ),
    )
    company_phone = forms.CharField(
        max_length=40,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "(000) 867-5309"}
        ),
    )
    first_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "John"}),
        required=False,
    )
    company_logo = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}), required=False
    )


class SellerCommunicationForm(forms.Form):
    dispatch_email = forms.EmailField(
        max_length=255,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "dispatch@company.com"}
        ),
        required=False,
    )
    dispatch_phone = forms.CharField(
        max_length=40,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "(000) 867-5309"}
        ),
        required=False,
    )


class SellerAboutUsForm(forms.Form):
    about_us = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": "4"}),
        required=False,
    )
