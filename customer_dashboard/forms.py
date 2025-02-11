import datetime

from django import forms
from django.core.exceptions import ValidationError

from api.models import (
    Branding,
    UserAddress,
    UserAddressType,
    UserGroup,
    UserGroupLegal,
    User,
    Order,
    OrderGroup,
    OrderGroupAttachment,
    OrderReview,
)
from common.utils.state_sales_tax import STATE_CHOICES
from common.forms import HiddenDeleteFormSet
from common.models.choices.user_type import UserType
from crm.models import Lead, LeadNote, UserSelectableLeadStatus


def validate_swap_start_date(value):
    allowed_start_date = datetime.date.today()
    if value < allowed_start_date:
        raise ValidationError(
            "Date must be equal to or greater than: %(allowed_start_date)s",
            params={"allowed_start_date": allowed_start_date},
        )


def validate_start_date(value):
    allowed_start_date = datetime.date.today() + datetime.timedelta(days=1)
    if value < allowed_start_date:
        raise ValidationError(
            "Date must be equal to or greater than: %(allowed_start_date)s",
            params={"allowed_start_date": allowed_start_date},
        )


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


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "apollo_id",
            "phone",
            "email",
            "source",
            "type",
            "photo",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "apollo_id": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.TextInput(attrs={"class": "form-control"}),
            "source": forms.Select(attrs={"class": "form-select"}),
            "type": forms.Select(attrs={"class": "form-select"}),
            "photo": forms.ClearableFileInput(
                attrs={"type": "file", "class": "form-control"}
            ),
        }

    def __init__(self, *args, **kwargs):
        user_instance = kwargs.get("instance", None)
        auth_user = kwargs.pop("auth_user", None)
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields["photo"].label = "Profile Picture"
        self.fields["email"].disabled = True

        if user_instance and user_instance.is_staff:
            # Staff members don't need to fill out "How did you find us?"
            self.fields["source"].required = False
            self.fields["source"].widget = forms.HiddenInput()
        if not (auth_user and (auth_user.is_staff or auth_user.type == UserType.ADMIN)):
            # Only admins or impersonating staff can change user type
            self.fields["type"].disabled = True


# there is another UserInviteForm in supplier_dashboard
class UserInviteForm(forms.Form):
    first_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=True,
    )
    last_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=False,
    )
    email = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=True,
    )
    phone = forms.CharField(
        max_length=40,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=False,
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
        label="instructions",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
            }
        ),
    )
    delivered_to_street = forms.BooleanField(
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "role": "switch"}
        ),
        required=False,
    )


class OrderGroupAttachmentsForm(forms.ModelForm):
    class Meta:
        model = OrderGroupAttachment
        fields = ["file"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


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
    project_id = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=False,
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
    state = forms.ChoiceField(
        choices=STATE_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "autocomplete": "address-level1",
            }
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
    is_archived = forms.BooleanField(
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
    tax_exempt_status = forms.ChoiceField(
        choices=UserGroup.TaxExemptStatus.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
        help_text="Defaults to Account Exempt Status, but overrides if set.",
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        auth_user = kwargs.pop("auth_user", None)
        super(UserAddressForm, self).__init__(*args, **kwargs)
        if auth_user and not auth_user.is_staff:
            self.fields["is_archived"].widget = forms.HiddenInput()


class UserGroupForm(forms.ModelForm):
    class Meta:
        model = UserGroup
        fields = [
            "name",
            "account_owner",
            # "apollo_id",
            "pay_later",
            "industry",
            "share_code",
            # "compliance_status",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "account_owner": forms.Select(attrs={"class": "form-select"}),
            # "apollo_id": forms.TextInput(attrs={"class": "form-control"}),
            "pay_later": forms.HiddenInput(),
            "industry": forms.Select(attrs={"class": "form-select"}),
            "share_code": forms.TextInput(attrs={"class": "form-control"}),
            # "compliance_status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        auth_user = kwargs.pop("auth_user", None)
        super(UserGroupForm, self).__init__(*args, **kwargs)

        # Update the possible account owners
        self.fields["account_owner"].queryset = User.customer_team_users.all()

        # Make Apollo ID required
        # self.fields["apollo_id"].required = True
        self.fields["share_code"].disabled = True

        # Update field visibility based on user type
        if auth_user and not auth_user.is_staff:
            self.fields["share_code"].widget = forms.HiddenInput()
            self.fields["account_owner"].disabled = True
            self.fields["account_owner"].widget = forms.HiddenInput()
            # self.fields["compliance_status"].disabled = True
            # self.fields["compliance_status"].widget = forms.HiddenInput()
            # self.fields["apollo_id"].required = False
            # self.fields["apollo_id"].widget = forms.HiddenInput()


class paymentDetailsForm(forms.ModelForm):
    class Meta:
        model = UserGroup
        fields = [
            "credit_line_limit",
            "net_terms",
            "invoice_frequency",
            "autopay",
            "invoice_at_project_completion",
            "invoice_day_of_month",
            "tax_exempt_status",
        ]
        widgets = {
            "net_terms": forms.Select(attrs={"class": "form-select"}),
            "invoice_frequency": forms.Select(attrs={"class": "form-select"}),
            "invoice_day_of_month": forms.NumberInput(attrs={"class": "form-control"}),
            "autopay": forms.CheckboxInput(
                attrs={"class": "form-check-input", "role": "switch"}
            ),
            "invoice_at_project_completion": forms.CheckboxInput(
                attrs={"class": "form-check-input", "role": "switch"}
            ),
            "credit_line_limit": forms.NumberInput(attrs={"class": "form-control"}),
            "tax_exempt_status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        auth_user = kwargs.pop("auth_user", None)
        super(paymentDetailsForm, self).__init__(*args, **kwargs)
        # Update field visibility based on user type
        if auth_user and not auth_user.is_staff:
            self.fields["net_terms"].disabled = True
            self.fields["invoice_frequency"].disabled = True
            self.fields["autopay"].widget = forms.HiddenInput()
            self.fields["invoice_day_of_month"].disabled = True
            self.fields["credit_line_limit"].disabled = True
            self.fields["tax_exempt_status"].disabled = True


class UserGroupNewForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        auth_user = kwargs.pop("auth_user", None)
        super(UserGroupNewForm, self).__init__(*args, **kwargs)


# Create an Order form
class OrderGroupForm(forms.Form):
    user_address = forms.CharField(
        widget=forms.HiddenInput(),
    )
    product_waste_types = forms.ChoiceField(
        label="Material",
        help_text="Select majority material to be placed in dumpster.",
        choices=[],
        widget=forms.Select(
            attrs={"class": "form-select", "required": "true"}  # "multiple": "true",
        ),
        required=True,
    )
    delivery_date = forms.DateField(
        validators=[validate_start_date],
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "min": datetime.date.today() + datetime.timedelta(days=1),
            }
        ),
        required=True,
    )
    removal_date = forms.DateField(
        validators=[validate_start_date],
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "min": datetime.date.today() + datetime.timedelta(days=1),
            }
        ),
        label="Est. Removal Date",
    )
    # Create a choice field for service times per week, where the choices are 1-5 times per week.
    times_per_week = forms.ChoiceField(
        label="Service Times Per Week",
        choices=[
            (0.5, "0.5"),
            (1, "1"),
            (2, "2"),
            (3, "3"),
            (4, "4"),
            (5, "5"),
        ],
        widget=forms.RadioSelect(attrs={"class": "btn-check"}),
        help_text="Select the number of times per week",
        initial=1,
        required=True,
    )
    # Create a choice field for shift count. Only required if the product has rental_multi_step.
    schedule_window = forms.ChoiceField(
        choices=[
            ("Anytime (7am-4pm)", "Anytime (7am-4pm)"),
            ("Morning (7am-11am)", "Morning (7am-11am)"),
            ("Afternoon (12pm-4pm)", "Afternoon (12pm-4pm)"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Preferred Time of Day",
        required=True,
    )
    shift_count = forms.ChoiceField(
        label="Utilization",
        choices=[
            (OrderGroup.ShiftCount.ONE_SHIFT, "0 to 8 hours per day"),
            (OrderGroup.ShiftCount.TWO_SHIFTS, "9 to 16 hours per day"),
            (OrderGroup.ShiftCount.THREE_SHIFTS, "17 to 24 hours per day"),
        ],
        widget=forms.RadioSelect(attrs={"class": "btn-check"}),
        required=True,
        initial=OrderGroup.ShiftCount.ONE_SHIFT,
    )
    # Add is estimated end date checkbox
    # NOTE: Maybe also say that we will assume monthly rental for now.
    # is_estimated_end_date = forms.BooleanField(
    #     initial=False,
    #     widget=forms.CheckboxInput(
    #         attrs={"class": "form-check-input", "role": "switch"}
    #     ),
    #     required=False,
    # )
    quantity = forms.IntegerField(
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        initial=1,
        required=True,
        help_text="Note: Currently, the prices on the next page are always for one.",
    )

    def __init__(self, *args, **kwargs):
        user_addresses = kwargs.pop("user_addresses", None)
        product_waste_types = kwargs.pop("product_waste_types", None)
        product_add_ons = kwargs.pop("product_add_ons", None)
        self.main_product = kwargs.pop("main_product", None)

        super(OrderGroupForm, self).__init__(*args, **kwargs)

        if self.main_product.has_material:
            self.fields["product_waste_types"].choices = list(
                product_waste_types.values_list("id", "waste_type__name")
            )
        else:
            self.fields["product_waste_types"].widget = forms.HiddenInput()
            self.fields["product_waste_types"].required = False

        if not self.main_product.has_rental_multi_step:
            # Hide delivery and removal date fields
            # Change label of delivery date to service date
            self.fields["delivery_date"].label = "Service Date"
            self.fields["removal_date"].widget = forms.HiddenInput()
            # self.fields["is_estimated_end_date"].widget = forms.HiddenInput()
            self.fields["removal_date"].required = False
            # self.fields["is_estimated_end_date"].required = False

        if not self.main_product.has_service_times_per_week:
            self.fields["times_per_week"].widget = forms.HiddenInput()
            self.fields["times_per_week"].initial = None
            self.fields["times_per_week"].required = False

        # If the product does not have rental_multi_step, show the shift
        # count field.
        if not self.main_product.has_rental_multi_step:
            self.fields["shift_count"].widget = forms.HiddenInput()
            self.fields["shift_count"].required = False

    def clean_times_per_week(self):
        """Make sure not to pass times_per_week if the product does not support it."""
        times_per_week = self.cleaned_data["times_per_week"]
        if self.main_product.has_service_times_per_week and not times_per_week:
            raise ValidationError("This field is required.")
        if not self.main_product.has_service_times_per_week and times_per_week:
            return None
        return times_per_week

    def clean_delivery_date(self):
        # Do not allow delivery date to be on a Sunday.
        delivery_date = self.cleaned_data["delivery_date"]
        if delivery_date.weekday() == 6:  # 6 corresponds to Sunday
            user_address = self.cleaned_data["user_address"]
            allow_sunday_delivery = False
            if user_address:
                user_address_obj = UserAddress.objects.get(id=user_address)
                allow_sunday_delivery = user_address_obj.allow_sunday_delivery
            if not allow_sunday_delivery:
                raise ValidationError("Date cannot be on a Sunday.")
        elif delivery_date.weekday() == 5:
            user_address = self.cleaned_data["user_address"]
            allow_saturday_delivery = False
            if user_address:
                user_address_obj = UserAddress.objects.get(id=user_address)
                allow_saturday_delivery = user_address_obj.allow_saturday_delivery
            if not allow_saturday_delivery:
                raise ValidationError("Date cannot be on a Saturday.")
        return delivery_date

    def clean_removal_date(self):
        # https://docs.djangoproject.com/en/5.0/ref/forms/validation/
        delivery_date = self.cleaned_data["delivery_date"]
        removal_date = self.cleaned_data["removal_date"]
        if not delivery_date and not removal_date:
            # If both fields are empty, return the removal date as is.
            return removal_date
        if not delivery_date:
            raise ValidationError("date is required.")
        if removal_date and removal_date < delivery_date:
            raise ValidationError(
                "Removal date must be after delivery date: %(delivery_date)s",
                params={"delivery_date": delivery_date},
            )
        # Do not allow removal date to be on a Sunday.
        if removal_date and removal_date.weekday() == 6:  # 6 corresponds to Sunday
            raise ValidationError("Date cannot be on a Sunday.")
        # Always return a value to use as the new cleaned data, even if this method didn't change it.
        return removal_date


class OrderGroupSwapForm(forms.Form):
    order_group_id = forms.CharField(
        widget=forms.HiddenInput(),
    )
    order_group_start_date = forms.DateField(
        widget=forms.HiddenInput(),
    )
    swap_date = forms.DateField(
        validators=[validate_swap_start_date],
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "min": datetime.date.today(),
            }
        ),
    )
    schedule_window = forms.ChoiceField(
        choices=[
            ("Anytime (7am-4pm)", "Anytime (7am-4pm)"),
            ("Morning (7am-11am)", "Morning (7am-11am)"),
            ("Afternoon (12pm-4pm)", "Afternoon (12pm-4pm)"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    # is_removal = forms.BooleanField(
    #     initial=False,
    #     widget=forms.CheckboxInput(
    #         attrs={"class": "form-check-input", "role": "switch"}
    #     ),
    #     required=False,
    # )

    # NOTE: Below is an example of how to validate against a dynamic swap_date field.
    def __init__(self, *args, **kwargs):
        auth_user = kwargs.pop("auth_user", None)
        is_removal = kwargs.pop("is_removal", False)
        super(OrderGroupSwapForm, self).__init__(*args, **kwargs)
        # different label for is_removal
        if is_removal:
            self.fields["swap_date"].label = "Removal Date"
        # Do not allow same day swaps for customers
        # Set min attribute for swap_date input
        today = datetime.date.today()
        if hasattr(self, "cleaned_data"):
            start_date = self.cleaned_data.get("order_group_start_date")
        else:
            start_date = self.initial.get("order_group_start_date")
        # Check for null start_date because we only care about the initial form, not the POST form.
        min_date = today if start_date and start_date < today else start_date
        if min_date is None:
            min_date = today
        if auth_user and auth_user.is_staff:
            self.fields["swap_date"].widget.attrs["min"] = min_date
        else:
            self.fields["swap_date"].widget.attrs["min"] = (
                min_date + datetime.timedelta(days=1)
            )

    def clean_swap_date(self):
        # https://docs.djangoproject.com/en/5.0/ref/forms/validation/
        swap_date = self.cleaned_data["swap_date"]
        order_group_start_date = self.cleaned_data["order_group_start_date"]
        if swap_date < order_group_start_date:
            raise ValidationError(
                "Start date must be after the order group start date: %(allowed_start_date)s",
                params={"allowed_start_date": order_group_start_date},
            )

        # Always return a value to use as the new cleaned data, even if this method didn't change it.
        return swap_date


class OrderReviewForm(forms.ModelForm):
    class Meta:
        model = OrderReview
        fields = [
            "professionalism",
            "communication",
            "pricing",
            "timeliness",
            "comment",
        ]
        widgets = {
            "professionalism": forms.RadioSelect(),
            "communication": forms.RadioSelect(),
            "pricing": forms.RadioSelect(),
            "timeliness": forms.RadioSelect(),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class EditOrderDateForm(forms.Form):
    date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "min": datetime.date.today(),
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        order = kwargs.pop("instance", None)
        super(EditOrderDateForm, self).__init__(*args, **kwargs)
        self.user_address = order.order_group.user_address

    def clean_date(self):
        allowed_date = datetime.date.today() + datetime.timedelta(days=0)
        date = self.cleaned_data["date"]
        if date < allowed_date:
            raise ValidationError(
                "Must be after: %(allowed_date)s",
                params={"allowed_date": allowed_date - datetime.timedelta(days=1)},
            )
        elif date.weekday() == 6:  # 6 corresponds to Sunday
            allow_sunday_delivery = False
            if self.user_address:
                allow_sunday_delivery = self.user_address.allow_sunday_delivery
            if not allow_sunday_delivery:
                raise ValidationError("Date cannot be on a Sunday.")
        elif date.weekday() == 5:
            allow_saturday_delivery = False
            if self.user_address:
                allow_saturday_delivery = self.user_address.allow_saturday_delivery
            if not allow_saturday_delivery:
                raise ValidationError("Date cannot be on a Saturday.")
        return date


OrderReviewFormSet = forms.inlineformset_factory(
    Order, OrderReview, form=OrderReviewForm, formset=HiddenDeleteFormSet, extra=1
)


class CreditApplicationForm(forms.Form):
    structure = forms.ChoiceField(
        choices=UserGroupLegal.BusinessStructure.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Structure",
    )
    tax_id = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="EIN/TIN",
    )
    legal_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    doing_business_as = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=False,
        label="Doing Business As (DBA)",
    )
    industry = forms.ChoiceField(
        choices=UserGroupLegal.Industry.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    years_in_business = forms.IntegerField(
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        required=False,
    )
    estimated_monthly_revenue = forms.DecimalField(
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        required=False,
    )
    estimated_monthly_spend = forms.DecimalField(
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        required=False,
    )
    increase_credit = forms.DecimalField(
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        required=False,
        label="Increase Credit Limit",
        help_text="How much would you like to increase your credit limit by?",
    )
    street = forms.CharField(
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
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Zip Code",
    )
    accepts_terms = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, **kwargs):
        allow_increase = kwargs.pop("allow_increase", None)
        super(CreditApplicationForm, self).__init__(*args, **kwargs)
        if allow_increase:
            self.fields["increase_credit"].required = True
        else:
            self.fields["increase_credit"].widget = forms.HiddenInput()
            self.fields["increase_credit"].required = False


class BrandingForm(forms.ModelForm):
    class Meta:
        model = Branding
        fields = ["logo", "primary"]
        widgets = {
            "logo": forms.ClearableFileInput(
                attrs={"type": "file", "class": "form-control"}
            ),
            "primary": forms.TextInput(attrs={"type": "color", "id": "primary_color"}),
            # "secondary": forms.TextInput(attrs={"type": "color", "id": "secondary_color"}),
        }


# Using Formset to take advantage of inlineformset_factory, allowing to set UserGroup as instance
BrandingFormSet = forms.inlineformset_factory(
    UserGroup, Branding, form=BrandingForm, formset=HiddenDeleteFormSet, extra=1
)


class NewLeadForm(forms.ModelForm):
    """Form for creating a new lead or editing an existing lead with some automated fields."""

    class Meta:
        model = Lead
        fields = [
            "user",
            "user_address",
            "owner",
            "est_conversion_date",
            "est_value",
        ]
        widgets = {
            "user": forms.Select(attrs={"class": "form-select select-user"}),
            "user_address": forms.HiddenInput(),
            "owner": forms.Select(attrs={"class": "form-select select-user"}),
            "est_conversion_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "est_value": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super(NewLeadForm, self).__init__(*args, **kwargs)
        self.fields["owner"].queryset = User.sales_team_users.all()
        self.fields["user"].label_from_instance = (
            lambda obj: f"{obj.full_name}, {obj.email}" if obj.full_name else obj.email
        )
        self.fields["owner"].label_from_instance = (
            lambda obj: f"{obj.full_name or obj.email}"
        )

    def save(self, commit=True):
        lead = super().save(commit=False)
        # Automatically set lead type based on if user's company is a seller
        if lead.user.user_group and lead.user.user_group.seller:
            lead.type = Lead.Type.SELLER
        else:
            lead.type = Lead.Type.CUSTOMER

        if commit:
            lead.save()
        return lead


class LeadDetailForm(forms.ModelForm):
    """Form for editing a lead's details."""

    class Meta:
        model = Lead
        fields = [
            "user",
            "user_address",
            "owner",
            "est_conversion_date",
            "est_value",
            "status",
            "type",
        ]
        widgets = {
            "user": forms.Select(attrs={"class": "form-select", "required": "true"}),
            "user_address": forms.HiddenInput(),
            "owner": forms.Select(attrs={"class": "form-select"}),
            "est_conversion_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "est_value": forms.NumberInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select", "required": "true"}),
            "type": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super(LeadDetailForm, self).__init__(*args, **kwargs)
        # Update status choices to be current choice as well as any user-selectable (non-junk) statuses
        self.fields["status"].choices = [
            choice
            for choice in UserSelectableLeadStatus.choices
            if choice[0] != Lead.Status.JUNK
        ]
        if instance := kwargs.get("instance"):
            for choice in Lead.Status.choices:
                if choice[0] == instance.status:
                    self.fields["status"].choices.append(choice)
                    break

        self.fields["owner"].queryset = User.sales_team_users.all()
        self.fields["owner"].label_from_instance = (
            lambda obj: f"{obj.full_name or obj.email}"
        )
        self.fields["user"].label_from_instance = (
            lambda obj: f"{obj.full_name or obj.email}"
        )


class LeadNoteForm(forms.ModelForm):
    class Meta:
        model = LeadNote
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(
                attrs={
                    "cols": 30,
                    "rows": 2,
                    "class": "form-control",
                    "placeholder": "Add a note...",
                    "required": "true",
                }
            ),
        }


class BaseLeadNoteFormset(HiddenDeleteFormSet):
    """Formset to reverse the order of the forms (extra form first)."""

    def __iter__(self):
        return reversed(list(super(BaseLeadNoteFormset, self).__iter__()))

    def __getitem__(self, index):
        items = list(super(BaseLeadNoteFormset, self).__iter__())
        return items[-(index + 1)]
