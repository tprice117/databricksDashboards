from django import forms


class HiddenDeleteFormSet(forms.BaseInlineFormSet):
    """Using this formset to hide the delete field in the formset"""

    def add_fields(self, form, index):
        super().add_fields(form, index)
        if "DELETE" in form.fields:
            form.fields["DELETE"].widget = forms.HiddenInput()


class MultiTabularFormSet(forms.BaseInlineFormSet):
    template_name_table = "common/formsets/multi.html"

    def __init__(self, *args, **kwargs):
        self.empty_form_text = kwargs.pop("empty_form_text", "No items")
        super().__init__(*args, **kwargs)
