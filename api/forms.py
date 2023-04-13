from django import forms
from .models import *

class OpenDaysAdminForm(forms.ModelForm):
    open_days = forms.MultipleChoiceField(choices=Seller.open_day_choices, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Seller
        fields = '__all__'


# create forms file and to allow api to create data to db
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'user_id', 'phone', 'email', 'photo_url', 'seller', 'stripe_customer_id', 'device_token']
        # pwd later
        # widgets = {
        #    'password': forms.PasswordInput()}