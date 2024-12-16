from django import forms

from chat.models import Message
from api.models import (
    SellerLocation,
    SellerLocationMailingAddress,
    SellerProduct,
    SellerProductSellerLocation,
    Seller,
    UserGroup,
    User,
)
from common.forms import HiddenDeleteFormSet
from common.models.choices.user_type import UserType


class UserForm(forms.ModelForm):
    template_name = "supplier_dashboard/snippets/form.html"

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone",
            "type",
            "email",
            "photo",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "type": "tel"}),
            "type": forms.Select(attrs={"class": "form-select"}),
            "email": forms.TextInput(attrs={"class": "form-control", "type": "email"}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
        labels = {
            "photo": "Profile Picture",
        }

    def __init__(self, *args, **kwargs):
        auth_user = kwargs.pop("auth_user", None)
        user = kwargs.pop("user", None)
        instance = kwargs.get("instance")
        super(UserForm, self).__init__(*args, **kwargs)

        if instance:
            self.fields["email"].disabled = True
            self.fields["email"].required = False

        if auth_user and user and not auth_user.is_staff:
            # if auth_user.type is lower than user.type, then disable the type field.
            if auth_user.type == UserType.BILLING:
                if user.type == UserType.ADMIN:
                    self.fields["type"].disabled = True
                else:
                    self.fields["type"].choices = [
                        (UserType.BILLING, UserType.BILLING),
                        (UserType.MEMBER, UserType.MEMBER),
                    ]
            elif auth_user.type == UserType.MEMBER:
                if user.type == UserType.BILLING or user.type == UserType.ADMIN:
                    self.fields["type"].disabled = True
                else:
                    self.fields["type"].choices = [
                        (UserType.MEMBER, UserType.MEMBER),
                    ]
        elif auth_user:
            if auth_user.type == UserType.BILLING:
                self.fields["type"].choices = [
                    (UserType.BILLING, UserType.BILLING),
                    (UserType.MEMBER, UserType.MEMBER),
                ]
            elif auth_user.type == UserType.MEMBER:
                self.fields["type"].choices = [
                    (UserType.MEMBER, UserType.MEMBER),
                ]


class UserInviteForm(forms.Form):
    first_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=True,
    )
    last_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=True,
    )
    email = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=True,
    )
    type = forms.ChoiceField(
        choices=UserType.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        auth_user = kwargs.pop("auth_user", None)
        user = kwargs.pop("user", None)
        super(UserInviteForm, self).__init__(*args, **kwargs)
        if auth_user and user and not auth_user.is_staff:
            # if auth_user.type is lower than user.type, then disable the type field.
            if auth_user.type == UserType.BILLING:
                if user.type == UserType.ADMIN:
                    self.fields["type"].disabled = True
                else:
                    self.fields["type"].choices = [
                        (UserType.BILLING, UserType.BILLING),
                        (UserType.MEMBER, UserType.MEMBER),
                    ]
            elif auth_user.type == UserType.MEMBER:
                if user.type == UserType.BILLING or user.type == UserType.ADMIN:
                    self.fields["type"].disabled = True
                else:
                    self.fields["type"].choices = [
                        (UserType.MEMBER, UserType.MEMBER),
                    ]
        elif auth_user:
            if auth_user.type == UserType.BILLING:
                self.fields["type"].choices = [
                    (UserType.BILLING, UserType.BILLING),
                    (UserType.MEMBER, UserType.MEMBER),
                ]
            elif auth_user.type == UserType.MEMBER:
                self.fields["type"].choices = [
                    (UserType.MEMBER, UserType.MEMBER),
                ]


# SellerForm but using model form
class SellerForm(forms.ModelForm):
    class Meta:
        model = Seller
        fields = [
            "name",
            "phone",
            "website",
            "logo",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control", type: "tel"}),
            "website": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].required = True
        self.fields["phone"].required = True


class NewSellerForm(forms.ModelForm):
    template_name = "supplier_dashboard/snippets/form.html"

    apollo_id = forms.CharField(
        max_length=128,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Apollo ID",
        required=True,
    )

    class Meta:
        model = Seller
        fields = [
            "name",
            "phone",
            "website",
            "logo",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "type": "tel"}),
            "website": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].required = True
        # Change ordering of fields
        self.fields = {
            "name": self.fields["name"],
            "apollo_id": self.fields["apollo_id"],
            "phone": self.fields["phone"],
            "website": self.fields["website"],
            "logo": self.fields["logo"],
        }

    def save(self, commit=True):
        seller = super().save(commit=False)
        if commit:
            seller.save()
            UserGroup.objects.create(
                seller=seller,
                name=self.cleaned_data["name"],
                apollo_id=self.cleaned_data["apollo_id"],
            )
        return seller


class SellerUserForm(UserForm):
    class Meta(UserForm.Meta):
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            user = User.objects.get(email__iexact=email)
            if user.user_group:
                raise forms.ValidationError(
                    "User with this email is already a member of a Company.",
                )
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.type = UserType.ADMIN
        if commit:
            user.save()
        return user


UserInlineFormSet = forms.inlineformset_factory(
    UserGroup,
    User,
    form=SellerUserForm,
    formset=HiddenDeleteFormSet,
    can_delete=True,
    extra=1,
)


class SellerLocationForm(forms.ModelForm):
    template_name = "supplier_dashboard/snippets/location_form.html"

    mailing_street = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Mailing Address (Send Checks To)",
        required=True,
    )
    mailing_city = forms.CharField(
        max_length=40,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="City",
        required=True,
    )
    mailing_state = forms.CharField(
        max_length=2,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="State",
        required=True,
    )
    mailing_postal_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Zip Code",
        required=True,
    )

    class Meta:
        model = SellerLocation
        fields = [
            "order_email",
            "order_phone",
            "open_days",
            "open_time",
            "close_time",
            "payee_name",
            "street",
            "city",
            "state",
            "postal_code",
            "location_logo_image",
        ]
        widgets = {
            "order_email": forms.TextInput(
                attrs={"class": "form-control", "type": "email"}
            ),
            "order_phone": forms.TextInput(
                attrs={"class": "form-control", "type": "tel"}
            ),
            "open_days": forms.CheckboxSelectMultiple(
                attrs={"class": "form-check-input"}
            ),
            "open_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "close_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "payee_name": forms.TextInput(attrs={"class": "form-control"}),
            "street": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "location_logo_image": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
        }
        labels = {
            "open_days": "Open On",
            "open_time": "Open From",
            "close_time": "Open Until",
            "street": "Inventory Address",
            "postal_code": "Zip Code",
            "payee_name": "Make Payable To",
            "location_logo_image": "Location Logo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["open_days"].required = True
        self.fields["open_time"].required = True
        self.fields["close_time"].required = True
        self.fields["street"].required = True
        self.fields["order_email"].required = True
        self.fields["payee_name"].required = True

        self.fields["state"].widget.attrs["maxlength"] = 2

    def clean(self):
        cleaned_data = super().clean()

        state = cleaned_data.get("state")
        if state and (len(state) != 2 or not state.isalpha()):
            self.add_error("state", "State must be a two-letter abbreviation.")

        mailing_state = cleaned_data.get("mailing_state")
        if mailing_state and (len(mailing_state) != 2 or not mailing_state.isalpha()):
            self.add_error("mailing_state", "State must be a two-letter abbreviation.")

        return cleaned_data

    def save(self, commit=True):
        seller_location = super().save(commit=False)
        seller_location.state = self.cleaned_data["state"].upper()
        seller_location.country = "US"
        seller_location.name = f"{seller_location.seller.name} - {seller_location.city}"
        if commit:
            seller_location.save()
            SellerLocationMailingAddress.objects.create(
                seller_location=seller_location,
                street=self.cleaned_data["mailing_street"],
                city=self.cleaned_data["mailing_city"],
                state=self.cleaned_data["mailing_state"].upper(),
                postal_code=self.cleaned_data["mailing_postal_code"],
                country="US",
            )
        return seller_location


SellerLocationInlineFormSet = forms.inlineformset_factory(
    Seller,
    SellerLocation,
    form=SellerLocationForm,
    formset=HiddenDeleteFormSet,
    can_delete=True,
    extra=1,
)


class ProductLocationForm(forms.Form):
    """Form for adding locations to a product. (For creating SellerProductSellerLocation records)"""

    product_id = forms.CharField(max_length=255, widget=forms.HiddenInput())
    product_code = forms.CharField(
        max_length=255,
        widget=forms.HiddenInput(),
        required=False,
    )
    add_ons = forms.CharField(
        max_length=255,
        widget=forms.HiddenInput(),
        required=False,
    )
    locations = forms.MultipleChoiceField(
        choices=[],
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-control",
                "name": "choices-multiple-remove-button",
                "data-placeholder": "Select locations",
            }
        ),
        required=False,
    )

    def clean_locations(self):
        """Raises an error if the user tries to remove locations."""
        locations = self.cleaned_data["locations"]
        if not set(self.initial.get("locations", [])).issubset(set(locations)):
            raise forms.ValidationError("Cannot remove locations.")
        return locations

    def save(self, seller):
        """
        Saves the seller's product locations.

        This method processes the cleaned data from the form, specifically the product_id and locations.
        It creates a SellerProduct if it does not already exist for the given seller and product_id.
        It then determines which new locations need to be added for the seller's product and returns
        a list of SellerProductSellerLocation instances for those new locations.

        Args:
            seller (Seller): The seller instance for whom the product locations are being saved.

        Returns:
            list: A list of SellerProductSellerLocation instances representing the new locations
                  that need to be added for the seller's product. If no new locations are added,
                  an empty list is returned.
        """
        product_id = self.cleaned_data["product_id"]
        locations = self.cleaned_data["locations"]

        if not locations or set(locations) == set(self.initial.get("locations", [])):
            return []

        # Create SellerProduct if it doesn't exist
        seller_product, created = SellerProduct.objects.get_or_create(
            seller=seller,
            product_id=product_id,
        )

        # Get all existing location_ids for the given product_id
        existing_location_ids = set(
            str(location_id)
            for location_id in SellerProductSellerLocation.objects.filter(
                seller_product_id=seller_product.id
            ).values_list("seller_location_id", flat=True)
        )
        # Determine which location_ids need to be created
        new_location_ids = set(locations) - existing_location_ids

        # Add new records to the list
        seller_product_seller_locations = []
        for location_id in new_location_ids:
            seller_location = SellerLocation.objects.get(id=location_id)
            seller_product_seller_locations.append(
                SellerProductSellerLocation(
                    seller_product=seller_product,
                    seller_location=seller_location,
                )
            )

        return seller_product_seller_locations


class BaseProductLocationFormSet(forms.BaseFormSet):
    """Formset to create multiple SellerProductSellerLocation records at once."""

    def __init__(self, *args, **kwargs):
        self.seller = kwargs.pop("seller", None)
        super().__init__(*args, **kwargs)
        self._set_location_choices()

    def _set_location_choices(self):
        """Sets the formatted location choices for each form in the formset."""
        self.choices = []
        if self.seller:
            locations = SellerLocation.objects.filter(seller=self.seller)
            self.choices = [
                (location.id, f"{location.street}, {location.city}")
                for location in locations
            ]
        for form in self.forms:
            form.fields["locations"].choices = self.choices

    def save(self):
        all_seller_product_seller_locations = []
        for form in self.forms:
            if form.cleaned_data:
                seller_product_seller_locations = form.save(self.seller)
                all_seller_product_seller_locations.extend(
                    seller_product_seller_locations
                )

        if all_seller_product_seller_locations:
            SellerProductSellerLocation.objects.bulk_create(
                all_seller_product_seller_locations
            )
            return True
        return False


ProductFormSet = forms.formset_factory(
    form=ProductLocationForm,
    formset=BaseProductLocationFormSet,
    extra=0,
    can_delete=False,
)


class SellerCommunicationForm(forms.Form):
    dispatch_email = forms.EmailField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=False,
    )
    dispatch_phone = forms.CharField(
        max_length=40,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=False,
    )


class SellerAboutUsForm(forms.Form):
    about_us = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": "4"}),
        required=False,
    )


# new form using forms.ModelForm
class SellerLocationComplianceForm(forms.ModelForm):
    class Meta:
        model = SellerLocation
        fields = [
            "gl_coi",
            "auto_coi",
            "workers_comp_coi",
            "w9",
            "location_logo_image",
            "open_days",
            "open_time",
            "close_time",
            "lead_time_hrs",
            "announcement",
            "live_menu_is_active",
        ]
        widgets = {
            "gl_coi": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "auto_coi": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "workers_comp_coi": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "w9": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "location_logo_image": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "open_days": forms.CheckboxSelectMultiple(),
            "open_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "close_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "lead_time_hrs": forms.NumberInput(attrs={"class": "form-control"}),
            "announcement": forms.Textarea(
                attrs={"class": "form-control", "rows": "4"}
            ),
            "live_menu_is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
        labels = {
            "gl_coi": "General Liability Proof of Insurance",
            "auto_coi": "Auto Proof of Insurance",
            "workers_comp_coi": "Workers Comp Proof of Insurance",
            "location_logo_image": "Logo",
            "lead_time_hrs": "Lead Time (in hours)",
        }


class SellerLocationComplianceAdminForm(forms.ModelForm):
    class Meta:
        model = SellerLocation
        fields = [
            "gl_coi",
            "gl_coi_expiration_date",
            "auto_coi",
            "auto_coi_expiration_date",
            "workers_comp_coi",
            "workers_comp_coi_expiration_date",
            "w9",
            "location_logo_image",
            "open_days",
            "open_time",
            "close_time",
            "lead_time_hrs",
            "announcement",
            "live_menu_is_active",
        ]
        widgets = {
            "gl_coi": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "gl_coi_expiration_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "auto_coi": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "auto_coi_expiration_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "workers_comp_coi": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "workers_comp_coi_expiration_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "w9": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "location_logo_image": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "open_days": forms.CheckboxSelectMultiple(),
            "open_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "close_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "lead_time_hrs": forms.NumberInput(attrs={"class": "form-control"}),
            "announcement": forms.Textarea(
                attrs={"class": "form-control", "rows": "4"}
            ),
            "live_menu_is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
        # add labels
        labels = {
            "gl_coi": "General Liability Proof of Insurance",
            "gl_coi_expiration_date": "Expires on",
            "auto_coi": "Auto Proof of Insurance",
            "auto_coi_expiration_date": "Expires on",
            "workers_comp_coi": "Workers Comp Proof of Insurance",
            "workers_comp_coi_expiration_date": "Expires on",
            "location_logo_image": "Logo",
            "lead_time_hrs": "Lead Time (in hours)",
        }


class SellerPayoutForm(forms.Form):
    payee_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    street = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    city = forms.CharField(
        max_length=40,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    state = forms.CharField(
        max_length=80,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    postal_code = forms.CharField(
        label="Zip Code",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


class ChatMessageForm(forms.ModelForm):
    message = forms.CharField(
        label="",
        widget=forms.Textarea(
            attrs={
                "id": "chat-message-input",
                "class": "form-control flex-grow-1 me-2",
                "rows": 1,
                "oninput": "autoResize(this)",
                "tabindex": "0",
                "style": "height: 92px; overflow-y: hidden;",
            }
        ),
    )

    class Meta:
        model = Message
        fields = [
            "message",
        ]
