from django import forms

from chat.models import Message
from api.models import SellerLocation, Seller
from common.models.choices.user_type import UserType


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
    type = forms.ChoiceField(
        choices=UserType.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    email = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=False,
        disabled=True,
    )
    photo = forms.ImageField(
        label="Profile Picture",
        widget=forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        auth_user = kwargs.pop("auth_user", None)
        user = kwargs.pop("user", None)
        super(UserForm, self).__init__(*args, **kwargs)
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
        required=False,
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
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "website": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].required = True
        self.fields["phone"].required = True

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
            "gl_coi": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "auto_coi": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "workers_comp_coi": forms.ClearableFileInput(
                attrs={"class": "form-control-file"}
            ),
            "w9": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "location_logo_image": forms.ClearableFileInput(
                attrs={"class": "form-control-file"}
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
            "gl_coi": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "gl_coi_expiration_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "auto_coi": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "auto_coi_expiration_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "workers_comp_coi": forms.ClearableFileInput(
                attrs={"class": "form-control-file"}
            ),
            "workers_comp_coi_expiration_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "w9": forms.ClearableFileInput(attrs={"class": "form-control-file"}),
            "location_logo_image": forms.ClearableFileInput(
                attrs={"class": "form-control-file"}
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
