from crispy_forms.helper import FormHelper
from crispy_forms.layout import Fieldset, Layout, Submit
from dal import autocomplete
from django import forms
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from .models import Book, BookRole, Work, WorkRole


########
# Work #
########
class WorkForm(forms.ModelForm):
    class Meta:
        model = Work
        exclude = ["created_by", "updated_by", "persons"]
        fields = "__all__"
        help_texts = {
            "title": "Enter the work's title in its original language. ",
            "publication_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[
            "language"
        ].help_text = "Enter the language of the work in its original language. E.g. English, 日本語, etc."
        self.fields["work_type"].label = "Type"
        self.fields["work_type"].help_text = "e.g. novel, short story, poem, etc."


class WorkRoleForm(forms.ModelForm):
    class Meta:
        model = WorkRole
        fields = ["person", "role"]


WorkRoleFormSet = inlineformset_factory(
    Work,
    WorkRole,
    form=WorkRoleForm,
    extra=20,
    can_delete=False,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:person-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:person_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)


########
# Book #
########
class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        exclude = ["created_by", "updated_by", "persons"]
        fields = "__all__"
        widgets = {
            "work": autocomplete.ModelSelect2(
                url=reverse_lazy("read:work-autocomplete")
            ),
            "publisher": autocomplete.ModelSelect2(
                url=reverse_lazy("read:publisher-autocomplete")
            ),
        }


class BookRoleForm(forms.ModelForm):
    class Meta:
        model = BookRole
        fields = ("person", "role", "name")


BookRoleFormSet = inlineformset_factory(
    Book,
    BookRole,
    form=BookRoleForm,
    extra=20,
    can_delete=False,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:person-autocomplete")
        ),
        "role": autocomplete.ModelSelect2(url=reverse_lazy("entity:role-autocomplete")),
    },
)
