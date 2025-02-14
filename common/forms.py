from django import forms

from common.models import NoteModel


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


class NoteForm(forms.ModelForm):
    class Meta:
        model = NoteModel
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(
                attrs={
                    "cols": 30,
                    "rows": 2,
                    "class": "form-control",
                    "placeholder": "Add a note...",
                    "required": "true",
                }
            ),
        }

    def clean_text(self):
        text = self.cleaned_data["text"]
        if not text.strip():
            raise forms.ValidationError("Note cannot be empty.")
        return text

    def clean(self):
        if not self.cleaned_data.get("text"):
            raise forms.ValidationError("Note cannot be empty.")
        return super().clean()


class BaseNoteFormset(HiddenDeleteFormSet):
    """Formset to reverse the order of the forms (extra form first)."""

    def __iter__(self):
        return reversed(list(super(BaseNoteFormset, self).__iter__()))

    def __getitem__(self, index):
        items = list(super(BaseNoteFormset, self).__iter__())
        return items[-(index + 1)]
