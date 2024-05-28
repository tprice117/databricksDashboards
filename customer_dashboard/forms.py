from django import forms
from api.models.user.user_address_type import UserAddressType


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
                "placeholder": "Placement details for delivery",
                "rows": 3,
            }
        )
    )


# Create a User Address form
class UserAddressForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Home"}),
    )
    all_address_types = get_all_address_types()
    address_type = forms.ChoiceField(
        choices=all_address_types,
        widget=forms.Select(attrs={"class": "form-control"}),
        required=False,
    )
    street = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "1234 Main St",
            }
        )
    )
    city = forms.CharField(
        max_length=40,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Anytown"}
        ),
    )
    state = forms.CharField(
        max_length=80,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "CA"}),
    )
    postal_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "90210"}),
    )
    country = forms.CharField(
        initial="US",
        max_length=80,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "US"}),
        disabled=True,
    )
    is_archived = forms.BooleanField(
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        required=False,
    )
    allow_saturday_delivery = forms.BooleanField(
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        required=False,
    )
    allow_sunday_delivery = forms.BooleanField(
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        required=False,
    )
    access_details = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": "Access details for this location",
                "rows": 3,
            }
        ),
        required=False,
    )
