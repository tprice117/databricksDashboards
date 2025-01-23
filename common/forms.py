from django import forms


class HiddenDeleteFormSet(forms.BaseInlineFormSet):
    """Using this formset to hide the delete field in the formset"""

    def add_fields(self, form, index):
        super().add_fields(form, index)
        if "DELETE" in form.fields:
            form.fields["DELETE"].widget = forms.HiddenInput()


class MultiTabularFormSet(forms.BaseInlineFormSet):
    template_name_table = "common/formsets/multi.html"

    @property
    def empty_form(self):
        """
        Returns an empty form for the formset.
        """
        form = self.form(
            auto_id=self.auto_id,
            prefix=self.add_prefix("__prefix__"),
            empty_permitted=True,
            use_required_attribute=False,
            **self.get_form_kwargs(None),
        )
        return form

    def __init__(self, *args, **kwargs):
        self.empty_form_text = kwargs.pop("empty_form_text", "No items")
        super().__init__(*args, **kwargs)
