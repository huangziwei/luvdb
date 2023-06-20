from crispy_forms.helper import FormHelper
from crispy_forms.layout import Fieldset, Layout, Submit
from dal import autocomplete
from django import forms
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from .models import Book, BookRole, BookWork, BookWorkRole, Work, WorkRole


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
    domain = forms.CharField(initial="read", widget=forms.HiddenInput())

    class Meta:
        model = WorkRole
        fields = ["person", "role", "domain"]


WorkRoleFormSet = inlineformset_factory(
    Work,
    WorkRole,
    form=WorkRoleForm,
    extra=1,
    can_delete=True,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:person-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:person_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],  # forward the domain field to the RoleAutocomplete view
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
        exclude = ["created_by", "updated_by", "work_roles", "persons"]
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
    domain = forms.CharField(initial="read", widget=forms.HiddenInput())

    class Meta:
        model = BookRole
        fields = ("person", "role", "domain", "name")


BookRoleFormSet = inlineformset_factory(
    Book,
    BookRole,
    form=BookRoleForm,
    extra=10,
    can_delete=True,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:person-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:person_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],  # forward the domain field to the RoleAutocomplete view
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)


class BookWorkForm(forms.ModelForm):
    class Meta:
        model = BookWork
        fields = ["work", "order"]


BookWorkFormSet = inlineformset_factory(
    Book,  # parent model
    BookWork,  # inline model
    form=BookWorkForm,  # form to use
    extra=10,  # number of empty forms
    can_delete=True,  # allow deletion
    widgets={
        "work": autocomplete.ModelSelect2(
            url=reverse_lazy(
                "read:work-autocomplete"
            ),  # change "entity:work-autocomplete" to the correct url name
            attrs={
                "data-create-url": reverse_lazy("read:work_create")
            },  # change "entity:work_create" to the correct url name
        ),
    },
)


class BookWorkRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="read", widget=forms.HiddenInput())

    class Meta:
        model = BookWorkRole
        fields = ["work", "order", "person", "role", "domain", "name", "alt_title"]


BookWorkRoleFormSet = inlineformset_factory(
    Book,  # parent model
    BookWorkRole,  # inline model
    form=BookWorkRoleForm,  # form to use
    extra=10,  # number of empty forms
    can_delete=True,  # allow deletion
    widgets={
        "work": autocomplete.ModelSelect2(
            url=reverse_lazy("read:work-autocomplete"),
            attrs={"data-create-url": reverse_lazy("read:work_create")},
        ),
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:person-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:person_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)
