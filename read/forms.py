from crispy_forms.helper import FormHelper
from crispy_forms.layout import Fieldset, Layout, Submit
from dal import autocomplete
from django import forms
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from .models import Book, BookRole, Edition, EditionRole


########
# Book #
########
class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        exclude = ["created_by", "updated_by"]
        fields = "__all__"


class BookRoleForm(forms.ModelForm):
    class Meta:
        model = BookRole
        fields = ["person", "role"]


BookRoleFormSet = inlineformset_factory(
    Book,
    BookRole,
    form=BookRoleForm,
    extra=20,
    can_delete=False,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("read:person-autocomplete")
        ),
        "role": autocomplete.ModelSelect2(url=reverse_lazy("read:role-autocomplete")),
    },
)


###########
# Edition #
###########
class EditionForm(forms.ModelForm):
    class Meta:
        model = Edition
        exclude = ["created_by", "updated_by", "persons"]
        fields = "__all__"
        widgets = {
            "book": autocomplete.ModelSelect2(
                url=reverse_lazy("read:book-autocomplete")
            ),
            "publisher": autocomplete.ModelSelect2(
                url=reverse_lazy("read:publisher-autocomplete")
            ),
        }


class EditionRoleForm(forms.ModelForm):
    class Meta:
        model = EditionRole
        fields = ("person", "role", "name")


EditionRoleFormSet = inlineformset_factory(
    Edition,
    EditionRole,
    form=EditionRoleForm,
    extra=20,
    can_delete=False,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("read:person-autocomplete")
        ),
        "role": autocomplete.ModelSelect2(url=reverse_lazy("read:role-autocomplete")),
    },
)
