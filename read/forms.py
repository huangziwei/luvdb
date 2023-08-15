import re

from dal import autocomplete
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from .models import (
    Book,
    BookInSeries,
    BookInstance,
    BookRole,
    BookSeries,
    Instance,
    InstanceRole,
    Issue,
    IssueInstance,
    Periodical,
    ReadCheckIn,
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
            "genres": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("read:genre-autocomplete")
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["publication_date"].label = "First Publication Date"
        self.fields["language"].label = "Original Language"
        self.fields["work_type"].label = "Type"
        self.fields["work_type"].help_text = "e.g. novel, short story, poem, etc."
        self.fields["genres"].required = False


class WorkRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="read", widget=forms.HiddenInput())

    class Meta:
        model = WorkRole
        fields = ["person", "alt_name", "role", "domain"]

    def clean(self):
        cleaned_data = super().clean()
        person = cleaned_data.get("person")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if person and not role:
            raise ValidationError("Role is required when Person is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.person is None:  # if the person field is empty
            if commit and instance.pk:
                instance.delete()
            return None
        if commit:
            instance.save()
        return instance


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

        self.fields["publication_date"].label = "Publication Date"
        self.fields["language"].label = "Language"


class InstanceRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="read", widget=forms.HiddenInput())

    class Meta:
        model = InstanceRole
        fields = ["person", "alt_name", "role", "domain"]

    def clean(self):
        cleaned_data = super().clean()
        person = cleaned_data.get("person")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if person and not role:
            raise ValidationError("Role is required when Person is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.person is None:  # if the person field is empty
            if commit and instance.pk:
                instance.delete()
            return None
        if commit:
            instance.save()
        return instance


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
            "length": "e.g. 300 pages, 10:20:33, etc.",
            "publication_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`.",
        }

    def __init__(self, *args, **kwargs):
        super(BookForm, self).__init__(*args, **kwargs)
        self.fields["cover_sens"].label = "Is the cover sensitive or explicit?"


class BookRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="read", widget=forms.HiddenInput())

    class Meta:
        model = BookRole
        fields = ("person", "role", "domain", "alt_name")

    def clean(self):
        cleaned_data = super().clean()
        person = cleaned_data.get("person")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if person and not role:
            raise ValidationError("Role is required when Person is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.person is None:  # if the person field is empty
            if commit and instance.pk:
                instance.delete()
            return None
        if commit:
            instance.save()
        return instance


BookRoleFormSet = inlineformset_factory(
    Book,
    BookRole,
    form=BookRoleForm,
    extra=10,
    can_delete=True,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:person-autocomplete"),
            attrs={
                "data-create-url": reverse_lazy("entity:person_create"),
                "data-placeholder": "Type to search",
            },
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

    def clean(self):
        cleaned_data = super().clean()
        instance = cleaned_data.get("instance")
        if self.instance and not instance:  # if the instance field is empty
            self.instance.delete()  # delete the BookInstance instance
        return cleaned_data


BookInstanceFormSet = inlineformset_factory(
    Book,
    BookInstance,
    form=BookInstanceForm,
    extra=100,
    can_delete=True,
    widgets={
        "instance": autocomplete.ModelSelect2(
            url=reverse_lazy("read:instance-autocomplete"),
            attrs={
                "data-create-url": reverse_lazy("read:instance_create"),
                "data-placeholder": "Type to search",
            },
        ),
    },
)


class PeriodicalForm(forms.ModelForm):
    class Meta:
        model = Periodical
        fields = [
            "title",
            "subtitle",
            "frequency",
            "language",
            "issn",
            "wikipedia",
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
            "cover",
            "number",
            "volume",
            "publisher",
            "publication_date",
            "title",
            "internet_archive_url",
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
            "publisher": autocomplete.ModelSelect2(
                url=reverse_lazy("read:publisher-autocomplete")
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


class ReadCheckInForm(forms.ModelForm):
    class Meta:
        model = ReadCheckIn
        fields = [
            "content_type",
            "object_id",
            "user",
            "status",
            "progress",
            "progress_type",
            "content",
            "comments_enabled",
            "share_to_feed",
        ]
        widgets = {
            "content_type": forms.HiddenInput(),
            "object_id": forms.HiddenInput(),
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
        super(ReadCheckInForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""
        self.fields["content"].required = False


class BookSeriesForm(forms.ModelForm):
    class Meta:
        model = BookSeries
        fields = ["title"]


class BookInSeriesForm(forms.ModelForm):
    book_url = forms.URLField()

    class Meta:
        model = BookInSeries
        fields = ["book_url", "order"]
        exclude = ["series"]

    def clean_book_url(self):
        book_url = self.cleaned_data.get("book_url")
        if not book_url:  # if the field is empty, just return it
            return book_url
        book_id = re.findall(r"book/(\d+)", book_url)
        if not book_id:
            raise forms.ValidationError("Invalid Book URL")
        try:
            book = Book.objects.get(pk=book_id[0])
        except Book.DoesNotExist:
            raise forms.ValidationError("Book does not exist")
        self.instance.book = book  # save the book instance directly
        return book_url

    def clean(self):
        cleaned_data = super().clean()
        book_url = cleaned_data.get("book_url")
        if not book_url:  # if the book_url field is empty
            self.cleaned_data["DELETE"] = True  # mark the form for deletion
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(BookInSeriesForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.book:
            self.fields[
                "book_url"
            ].initial = f"{settings.ROOT_URL}/read/book/{self.instance.book.pk}"
        self.fields["book_url"].required = False
        self.fields["book_url"].label = "URL"
        self.fields["order"].required = False


BookInSeriesFormSet = forms.inlineformset_factory(
    BookSeries, BookInSeries, form=BookInSeriesForm, extra=2, can_delete=True
)
