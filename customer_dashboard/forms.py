from django import forms

from api.models import UserAddressType, UserGroup
from common.models.choices.user_type import UserType


def get_all_address_types(_social_site=None):
    try:
        type_list = [("", "----------")]
        all_address_types = UserAddressType.objects.all()
        for _obj in all_address_types:
            type_list.append((_obj.id, _obj.name))
    except Exception as e:
        type_list = [
            ("", "----------"),
            ("Residential", "Residential"),
            ("Construction", "Construction "),
            ("Apartments", "Apartments"),
            ("Other", "Other"),
        ]
    return type_list


class UserForm(forms.Form):
    first_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phone = forms.CharField(
        max_length=40,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=False,
    )
    email = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        disabled=True,
        required=False,
    )
    type = forms.ChoiceField(
        choices=UserType.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    photo = forms.ImageField(
        label="Profile Picture",
        widget=forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        required=False,
    )


class AccessDetailsForm(forms.Form):
    access_details = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": "Access details for delivery",
                "rows": 3,
            }
        )
    )


class PlacementDetailsForm(forms.Form):
    placement_details = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
            }
        )
    )


class UserAddressForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "organization",
            }
        ),
    )
    all_address_types = get_all_address_types()
    address_type = forms.ChoiceField(
        choices=all_address_types,
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
    )
    street = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "street-address",
            }
        )
    )
    city = forms.CharField(
        max_length=40,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "address-level2",
            }
        ),
    )
    state = forms.CharField(
        max_length=80,
        widget=forms.TextInput(
            attrs={"class": "form-control", "autocomplete": "address-level1"}
        ),
    )
    postal_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "postal-code",
            }
        ),
    )
    country = forms.CharField(
        initial="US",
        max_length=80,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "US"}),
        disabled=True,
    )
    autopay = forms.BooleanField(
        initial=False,
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "role": "switch"}
        ),
        required=False,
    )
    is_archived = forms.BooleanField(
        initial=False,
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "role": "switch"}
        ),
        required=False,
    )
    allow_saturday_delivery = forms.BooleanField(
        initial=False,
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "role": "switch"}
        ),
        required=False,
    )
    allow_sunday_delivery = forms.BooleanField(
        initial=False,
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "role": "switch"}
        ),
        required=False,
    )
    access_details = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
            }
        ),
        required=False,
    )


class UserGroupForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    pay_later = forms.BooleanField(
        initial=False,
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "role": "switch"}
        ),
        required=False,
    )
    autopay = forms.BooleanField(
        initial=False,
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "role": "switch"}
        ),
        required=False,
    )
    net_terms = forms.ChoiceField(
        choices=UserGroup.NetTerms.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
    )
    invoice_frequency = forms.ChoiceField(
        choices=UserGroup.InvoiceFrequency.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
    )
    invoice_day_of_month = forms.IntegerField(
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        required=False,
    )
    invoice_at_project_completion = forms.BooleanField(
        initial=False,
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "role": "switch"}
        ),
        required=False,
    )
    share_code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=False,
        disabled=True,
    )
    credit_line_limit = forms.DecimalField(
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        required=False,
    )
    compliance_status = forms.ChoiceField(
        choices=UserGroup.COMPLIANCE_STATUS_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        initial="NOT_REQUIRED",
    )
    tax_exempt_status = forms.ChoiceField(
        choices=UserGroup.TaxExemptStatus.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        initial=UserGroup.TaxExemptStatus.NONE,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super(UserGroupForm, self).__init__(*args, **kwargs)
        if user and not user.is_staff:
            self.fields["net_terms"].disabled = True
            self.fields["share_code"].disabled = True
            self.fields["share_code"].widget = forms.HiddenInput()
            self.fields["credit_line_limit"].disabled = True
            self.fields["compliance_status"].disabled = True
            self.fields["tax_exempt_status"].disabled = True
