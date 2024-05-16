from django import forms


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
