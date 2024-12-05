from django import forms

from chat.models import Message
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


class SellerForm(forms.Form):
    company_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    company_phone = forms.CharField(
        max_length=40,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    website = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=False,
    )
    company_logo = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}), required=False
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


class SellerLocationComplianceForm(forms.Form):
    gl_coi = forms.FileField(
        label="General Liability Proof of Insurance",
        widget=forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        required=False,
    )
    gl_coi_expiration_date = forms.DateField(
        label="Expires on",
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "disabled": True}
        ),
        required=False,
    )

    auto_coi = forms.FileField(
        label="Auto Proof of Insurance",
        widget=forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        required=False,
    )
    auto_coi_expiration_date = forms.DateField(
        label="Expires on",
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "disabled": True,
            }
        ),
        required=False,
    )

    workers_comp_coi = forms.FileField(
        label="Workers Comp Proof of Insurance",
        widget=forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        required=False,
    )
    workers_comp_coi_expiration_date = forms.DateField(
        label="Expires on",
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "disabled": True,
            }
        ),
        required=False,
    )

    w9 = forms.FileField(
        label="Form W9",
        widget=forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        required=False,
    )


class SellerLocationComplianceAdminForm(forms.Form):
    gl_coi = forms.FileField(
        label="General Liability Proof of Insurance",
        widget=forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        required=False,
    )
    gl_coi_expiration_date = forms.DateField(
        label="Expires on",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        required=False,
    )

    auto_coi = forms.FileField(
        label="Auto Proof of Insurance",
        widget=forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        required=False,
    )
    auto_coi_expiration_date = forms.DateField(
        label="Expires on",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        required=False,
    )

    workers_comp_coi = forms.FileField(
        label="Workers Comp Proof of Insurance",
        widget=forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        required=False,
    )
    workers_comp_coi_expiration_date = forms.DateField(
        label="Expires on",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        required=False,
    )

    w9 = forms.FileField(
        label="Form W9",
        widget=forms.ClearableFileInput(attrs={"class": "form-control-file"}),
        required=False,
    )


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
