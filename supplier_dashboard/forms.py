from django import forms


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
    )
    email = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
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
