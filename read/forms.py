from crispy_forms.bootstrap import Field
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Fieldset, Layout, Row, Submit
from dal import autocomplete
from django import forms
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from .models import (
    Book,
    BookCheckIn,
    BookEdition,
    BookRole,
    BookWork,
    BookWorkRole,
    Edition,
    EditionRole,
    Work,
    WorkRole,
)


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

        self.fields["publication_date"].label = "First Publication Date"
        self.fields["language"].label = "Original Language"
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
    extra=15,
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


###########
# Edition #
###########
class EditionForm(forms.ModelForm):
    class Meta:
        model = Edition
        exclude = ["created_by", "updated_by", "persons"]
        fields = "__all__"
        help_texts = {
            "title": "Enter the edition's title. ",
            "publication_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
        }
        widgets = {
            "work": autocomplete.ModelSelect2(
                url=reverse_lazy("read:work-autocomplete")
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["publication_date"].label = "First Publication Date"
        self.fields["language"].label = "Original Language"


class EditionRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="read", widget=forms.HiddenInput())

    class Meta:
        model = EditionRole
        fields = ["person", "alt_name", "role", "domain"]


EditionRoleFormSet = inlineformset_factory(
    Edition,
    EditionRole,
    form=EditionRoleForm,
    extra=15,
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
        exclude = [
            "created_by",
            "updated_by",
            "works",
            "editions",
            "persons",
        ]
        fields = "__all__"
        widgets = {
            "work": autocomplete.ModelSelect2(
                url=reverse_lazy("read:work-autocomplete")
            ),
            "edition": autocomplete.ModelSelect2(
                url=reverse_lazy("read:edition-autocomplete")
            ),
            "publisher": autocomplete.ModelSelect2(
                url=reverse_lazy("read:publisher-autocomplete")
            ),
        }


class BookRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="read", widget=forms.HiddenInput())

    class Meta:
        model = BookRole
        fields = ("person", "role", "domain", "alt_name")


BookRoleFormSet = inlineformset_factory(
    Book,
    BookRole,
    form=BookRoleForm,
    extra=15,
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
    Book,
    BookWork,
    form=BookWorkForm,
    extra=15,
    can_delete=True,
    widgets={
        "work": autocomplete.ModelSelect2(
            url=reverse_lazy("read:work-autocomplete"),
            attrs={"data-create-url": reverse_lazy("read:work_create")},
        ),
    },
)


class BookEditionForm(forms.ModelForm):
    class Meta:
        model = BookEdition
        fields = ["edition", "order"]


BookEditionFormSet = inlineformset_factory(
    Book,
    BookEdition,
    form=BookEditionForm,
    extra=15,
    can_delete=True,
    widgets={
        "edition": autocomplete.ModelSelect2(
            url=reverse_lazy("read:edition-autocomplete"),
            attrs={"data-create-url": reverse_lazy("read:edition_create")},
        ),
    },
)


class BookWorkRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="read", widget=forms.HiddenInput())

    class Meta:
        model = BookWorkRole
        fields = [
            "work",
            "order",
            "person",
            "role",
            "domain",
            "alt_name",
            "alt_title",
            "publication_date",
        ]


BookWorkRoleFormSet = inlineformset_factory(
    Book,  # parent model
    BookWorkRole,  # inline model
    form=BookWorkRoleForm,  # form to use
    extra=15,  # number of empty forms
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


class BookCheckInForm(forms.ModelForm):
    class Meta:
        model = BookCheckIn
        fields = [
            "book",
            "author",
            "status",
            "progress",
            "progress_type",
            "content",
            "comments_enabled",
            "share_to_feed",
        ]
        widgets = {
            "book": forms.HiddenInput(),
            "author": forms.HiddenInput(),  # author is now included
            # "status": forms.Select(choices=BookCheckIn.READING_STATUS_CHOICES),
            # "progress": forms.NumberInput(),
            # "progress_type": forms.Select(choices=BookCheckIn.PROGRESS_TYPE_CHOICES),
            # "share_to_feed": forms.CheckboxInput(),
            "content": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Check in...",
                    "id": "text-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super(BookCheckInForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""
        self.fields["content"].required = False
        # self.fields["comments_enabled"].label = "Enable comments"
