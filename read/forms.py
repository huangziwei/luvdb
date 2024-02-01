import re

import auto_prefetch
from dal import autocomplete
from django import forms
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from entity.models import Role

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
    class Meta(auto_prefetch.Model.Meta):
        model = Work
        exclude = [
            "created_by",
            "updated_by",
            "creators",
            "locked",
            "related_locations_hierarchy",
        ]
        fields = "__all__"
        help_texts = {
            "title": "Enter the work's title in its original language. ",
            "publication_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`. For works published before common era, use negative numbers, e.g. `-100`.",
            "related_locations": "Locations that are important to the work, e.g. the setting of the story, etc. <a href='/visit/location/create/'>Add a new location</a>.",
            "notes": "Extra information about the work.",
        }
        widgets = {
            "language": autocomplete.ListSelect2(url="read:language-autocomplete"),
            "genres": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("read:genre-autocomplete")
            ),
            "publication_date": forms.TextInput(),
            "related_locations": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("visit:location-autocomplete")
            ),
            "based_on_litworks": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("read:work-autocomplete")
            ),
            "based_on_games": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("play:work-autocomplete")
            ),
            "based_on_movies": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("watch:movie-autocomplete")
            ),
            "based_on_series": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("watch:series-autocomplete")
            ),
            "mentioned_litworks": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("read:work-autocomplete")
            ),
            "mentioned_litinstances": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("read:instance-autocomplete")
            ),
            "mentioned_books": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("read:book-autocomplete")
            ),
            "mentioned_gameworks": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("play:work-autocomplete")
            ),
            "mentioned_games": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("play:work-autocomplete")
            ),
            "mentioned_movies": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("watch:movie-autocomplete")
            ),
            "mentioned_series": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("watch:series-autocomplete")
            ),
            "mentioned_locations": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("visit:location-autocomplete")
            ),
            "mentioned_musicalworks": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:work-autocomplete")
            ),
            "mentioned_tracks": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:track-autocomplete")
            ),
            "mentioned_releases": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:release-autocomplete")
            ),
        }
        labels = {
            "based_on_litworks": "Publications",
            "based_on_games": "Games",
            "based_on_movies": "Movies",
            "based_on_series": "Series",
            "mentioned_litworks": "Publication Works",
            "mentioned_litinstances": "Instances",
            "mentioned_books": "Books",
            "mentioned_gameworks": "Game Works",
            "mentioned_games": "Games",
            "mentioned_movies": "Movies",
            "mentioned_series": "Series",
            "mentioned_musicalworks": "Musical Works",
            "mentioned_tracks": "Tracks",
            "mentioned_releases": "Musical Releases",
            "mentioned_locations": "Locations",
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

    class Meta(auto_prefetch.Model.Meta):
        model = WorkRole
        fields = ["creator", "alt_name", "role", "domain"]

    def __init__(self, *args, **kwargs):
        super(WorkRoleForm, self).__init__(*args, **kwargs)
        # Set default role to "Performer"
        try:
            default_role = Role.objects.get(name="Author")
            self.fields["role"].initial = default_role
        except ObjectDoesNotExist:
            # If "Performer" role does not exist, the initial will be None as before
            pass

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if creator and not role:
            raise ValidationError("Role is required when Creator is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.creator is None:  # if the person field is empty
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
    extra=1,
    can_delete=True,
    widgets={
        "creator": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],  # forward the domain field to the RoleAutocomplete view
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
    help_texts={
        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
    },
)


###########
# Instance #
###########
class InstanceForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Instance
        exclude = ["created_by", "updated_by", "creators", "locked"]
        fields = "__all__"
        help_texts = {
            "title": "Enter the instance's title. ",
            "publication_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`. For instances published before common era, use negative numbers, e.g. `-100`.",
            "notes": "Extra information about the instance.",
        }
        widgets = {
            "work": autocomplete.ModelSelect2(
                url=reverse_lazy("read:work-autocomplete")
            ),
            "language": autocomplete.ListSelect2(url="read:language-autocomplete"),
            "publication_date": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["publication_date"].label = "Publication Date"
        self.fields["language"].label = "Language"


class InstanceRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="read", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = InstanceRole
        fields = ["creator", "alt_name", "role", "domain"]

    def __init__(self, *args, **kwargs):
        super(InstanceRoleForm, self).__init__(*args, **kwargs)
        # Set default role to "Performer"
        try:
            default_role = Role.objects.get(name="Author")
            self.fields["role"].initial = default_role
        except ObjectDoesNotExist:
            # If "Performer" role does not exist, the initial will be None as before
            pass

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if creator and not role:
            raise ValidationError("Role is required when Creator is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.creator is None:  # if the person field is empty
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
    extra=1,
    can_delete=True,
    widgets={
        "creator": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],  # forward the domain field to the RoleAutocomplete view
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
    help_texts={
        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
    },
)


########
# Book #
########
class BookForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Book
        exclude = [
            "created_by",
            "updated_by",
            "works",
            "instances",
            "creators",
            "locked",
        ]
        fields = "__all__"
        widgets = {
            "instance": autocomplete.ModelSelect2(
                url=reverse_lazy("read:instance-autocomplete")
            ),
            "publisher": autocomplete.ModelSelect2(
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "language": autocomplete.ListSelect2(url="read:language-autocomplete"),
            "publication_date": forms.TextInput(),
        }
        help_texts = {
            "format": "e.g. paperback, hardcover, ebook, etc.",
            "length": "e.g. 300 pages, 10:20:33, etc.",
            "publication_date": "Recommended formats: `YYYY`, `YYYY.MM` or `YYYY.MM.DD`. For books published before common era, use negative numbers, e.g. `-100`.",
            "publisher": "<a href='/entity/company/create/?next=/read/book/create/'>Add a new publisher</a>.",
            "instance": "<a href='/read/instance/create/'>Add a new instance</a>.",
            "notes": "Extra information about the book.",
        }

    def __init__(self, *args, **kwargs):
        super(BookForm, self).__init__(*args, **kwargs)
        self.fields["cover_sens"].label = "Is the cover sensitive or explicit?"
        self.fields["publisher"].required = False


class BookRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="read", widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super(BookRoleForm, self).__init__(*args, **kwargs)
        # Set default role to "Performer"
        try:
            default_role = Role.objects.get(name="Author")
            self.fields["role"].initial = default_role
        except ObjectDoesNotExist:
            # If "Performer" role does not exist, the initial will be None as before
            pass

    class Meta(auto_prefetch.Model.Meta):
        model = BookRole
        fields = ("creator", "role", "domain", "alt_name")

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")

        # if the person field is filled but the role field is not
        if creator and not cleaned_data.get("role"):
            raise ValidationError("Role is required when Creator is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.creator is None:
            # Only delete the instance if it has been saved before (i.e., it has a non-None id)
            if instance.pk and commit:
                instance.delete()
            return None
        if commit:
            instance.save()
        return instance


BookRoleFormSet = inlineformset_factory(
    Book,
    BookRole,
    form=BookRoleForm,
    extra=1,
    can_delete=True,
    widgets={
        "creator": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={
                "data-create-url": reverse_lazy("entity:creator_create"),
                "data-placeholder": "Type to search",
            },
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],  # forward the domain field to the RoleAutocomplete view
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
    help_texts={
        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
    },
)


class BookInstanceForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
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
    extra=1,
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
    help_texts={
        "instance": "<a href='/read/instance/create/'>Add a new instance</a>.",
    },
)


class PeriodicalForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
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
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "language": autocomplete.ListSelect2(url="read:language-autocomplete"),
        }


class IssueForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
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
                url=reverse_lazy("entity:company-autocomplete")
            ),
        }


class IssueInstanceForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = IssueInstance
        fields = ["instance", "order"]

    def clean(self):
        cleaned_data = super().clean()
        instance = cleaned_data.get("instance")
        if self.instance and not instance:  # if the instance field is empty
            self.instance.delete()  # delete the BookInstance instance
        return cleaned_data


IssueInstanceFormSet = inlineformset_factory(
    Issue,
    IssueInstance,
    form=IssueInstanceForm,
    extra=1,
    can_delete=True,
    widgets={
        "instance": autocomplete.ModelSelect2(
            url=reverse_lazy("read:instance-autocomplete"),
            attrs={"data-create-url": reverse_lazy("read:instance_create")},
        ),
    },
    help_texts={
        "instance": "<a href='/read/instance/create/'>Add a new instance</a>.",
    },
)


class ReadCheckInForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
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
    class Meta(auto_prefetch.Model.Meta):
        model = BookSeries
        fields = ["title", "notes"]


class BookInSeriesForm(forms.ModelForm):
    book_url = forms.URLField()

    class Meta(auto_prefetch.Model.Meta):
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
