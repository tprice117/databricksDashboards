from django import forms
from .models import *

# create forms file and to allow api to create data to db
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'user_id', 'phone', 'email', 'photo_url', 'stripe_customer_id', 'device_token']
        # pwd later
        # widgets = {
        #    'password': forms.PasswordInput()}