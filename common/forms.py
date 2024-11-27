from django import forms


class HiddenDeleteFormSet(forms.BaseInlineFormSet):
    """Using this formset to hide the delete field in the formset"""

    def add_fields(self, form, index):
        super().add_fields(form, index)
        if "DELETE" in form.fields:
            form.fields["DELETE"].widget = forms.HiddenInput()
