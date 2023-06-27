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
    BookInstance,
    BookRole,
    Instance,
    InstanceRole,
    Issue,
    IssueInstance,
    Periodical,
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
        widgets = {
            "language": autocomplete.ListSelect2(url="read:language-autocomplete"),
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
# Instance #
###########
class InstanceForm(forms.ModelForm):
    class Meta:
        model = Instance
        exclude = ["created_by", "updated_by", "persons"]
        fields = "__all__"
        help_texts = {
            "title": "Enter the instance's title. ",
            "publication_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
        }
        widgets = {
            "work": autocomplete.ModelSelect2(
                url=reverse_lazy("read:work-autocomplete")
            ),
            "language": autocomplete.ListSelect2(url="read:language-autocomplete"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["publication_date"].label = "First Publication Date"
        self.fields["language"].label = "Original Language"


class InstanceRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="read", widget=forms.HiddenInput())

    class Meta:
        model = InstanceRole
        fields = ["person", "alt_name", "role", "domain"]


InstanceRoleFormSet = inlineformset_factory(
    Instance,
    InstanceRole,
    form=InstanceRoleForm,
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
            "instances",
            "persons",
        ]
        fields = "__all__"
        widgets = {
            "work": autocomplete.ModelSelect2(
                url=reverse_lazy("read:work-autocomplete")
            ),
            "instance": autocomplete.ModelSelect2(
                url=reverse_lazy("read:instance-autocomplete")
            ),
            "publisher": autocomplete.ModelSelect2(
                url=reverse_lazy("read:publisher-autocomplete")
            ),
            "language": autocomplete.ListSelect2(url="read:language-autocomplete"),
        }
        help_texts = {
            "format": "e.g. paperback, hardcover, ebook, etc.",
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


class BookInstanceForm(forms.ModelForm):
    class Meta:
        model = BookInstance
        fields = ["instance", "order"]


BookInstanceFormSet = inlineformset_factory(
    Book,
    BookInstance,
    form=BookInstanceForm,
    extra=100,
    can_delete=True,
    widgets={
        "instance": autocomplete.ModelSelect2(
            url=reverse_lazy("read:instance-autocomplete"),
            attrs={"data-create-url": reverse_lazy("read:instance_create")},
        ),
    },
)


class PeriodicalForm(forms.ModelForm):
    class Meta:
        model = Periodical
        fields = [
            "title",
            "subtitle",
            "publisher",
            "frequency",
            "language",
            "issn",
            "website",
        ]

        widgets = {
            "publisher": autocomplete.ModelSelect2(
                url=reverse_lazy("read:publisher-autocomplete")
            ),
            "language": autocomplete.ListSelect2(url="read:language-autocomplete"),
        }


class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = [
            "periodical",
            "number",
            "volume",
            "publication_date",
            "title",
            "cover",
        ]
        exclude = [
            "created_by",
            "updated_by",
            "instances",
        ]
        widgets = {
            "instances": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("read:instance-autocomplete")
            ),
        }


class IssueInstanceForm(forms.ModelForm):
    class Meta:
        model = IssueInstance
        fields = ["instance", "order"]
        widgets = {
            "instance": autocomplete.ModelSelect2(
                url=reverse_lazy("read:instance-autocomplete"),
                attrs={"data-create-url": reverse_lazy("read:instance_create")},
            ),
        }


IssueInstanceFormSet = inlineformset_factory(
    Issue,
    IssueInstance,
    form=IssueInstanceForm,
    extra=100,
    can_delete=True,
)


class BookCheckInForm(forms.ModelForm):
    class Meta:
        model = BookCheckIn
        fields = [
            "book",
            "user",
            "status",
            "progress",
            "progress_type",
            "content",
            "comments_enabled",
            "share_to_feed",
        ]
        widgets = {
            "book": forms.HiddenInput(),
            "user": forms.HiddenInput(),  # user is now included
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
