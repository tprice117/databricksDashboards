from django import forms
from .models import *


class OpenDaysAdminForm(forms.ModelForm):
    class Meta:
        model = Seller
        fields = '__all__'

    def clean_open_days(self):
        open_days = self.cleaned_data.get('open_days')
        available_choices = [choice[0] for choice in self.fields['open_days'].choices]
        for selected_day in open_days:
            if selected_day not in available_choices:
                raise forms.ValidationError("Invalid choice selected for open_days.")
        return open_days


# create forms file and to allow api to create data to db
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'user_id', 'phone', 'email', 'photo_url', 'seller', 'stripe_customer_id', 'device_token']
        # pwd later
        # widgets = {
        #    'password': forms.PasswordInput()}