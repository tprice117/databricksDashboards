from django import forms
from .models import *

class OpenDaysAdminForm(forms.ModelForm):
    open_days = forms.MultipleChoiceField(choices=Seller.open_day_choices, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Seller
        fields = '__all__'
