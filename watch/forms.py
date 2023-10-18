import re

from crispy_forms.bootstrap import Field
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Fieldset, Layout, Row, Submit
from dal import autocomplete
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from .models import (
    Collection,
    ContentInCollection,
    Episode,
    EpisodeCast,
    EpisodeRole,
    Movie,
    MovieCast,
    MovieReleaseDate,
    MovieRole,
    Series,
    SeriesRole,
    WatchCheckIn,
)


class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        exclude = ["created_by", "updated_by", "creators", "casts"]
        fields = "__all__"
        widgets = {
            "studios": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "distributors": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "based_on": autocomplete.ModelSelect2(
                url=reverse_lazy("read:work-autocomplete")
            ),
            "genres": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("watch:genre-autocomplete")
            ),
            "other_titles": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super(MovieForm, self).__init__(*args, **kwargs)
        self.fields["studios_deprecated"].required = False
        self.fields["studios"].required = False
        self.fields["distributors"].required = False
        self.fields["genres"].required = False
        self.fields[
            "other_titles"
        ].help_text = (
            "e.g. translated titles in different languages, separated by slashes (`/`)."
        )


class MovieReleaseDateForm(forms.ModelForm):
    class Meta:
        model = MovieReleaseDate
        fields = ("region", "release_date")

    def clean(self):
        cleaned_data = super().clean()
        region = cleaned_data.get("region")
        release_date = cleaned_data.get("release_date")

        # if the region field is filled but the release_date field is not
        if region and not release_date:
            raise ValidationError("Release date is required when Region is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.region is None:
            if commit and instance.pk:
                instance.delete()
            return None
        if commit:
            instance.save()
        return instance


MovieReleaseDateFormSet = inlineformset_factory(
    Movie,
    MovieReleaseDate,
    form=MovieReleaseDateForm,
    extra=15,
    can_delete=True,
)


class MovieRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta:
        model = MovieRole
        fields = ("creator", "role", "domain", "alt_name")

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if person and not role:
            raise ValidationError("Role is required when Person is filled.")

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


MovieRoleFormSet = inlineformset_factory(
    Movie,
    MovieRole,
    form=MovieRoleForm,
    extra=15,
    can_delete=True,
    labels={"person": "Entity"},
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)


class MovieCastForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta:
        model = MovieCast
        fields = ("creator", "role", "domain", "character_name")

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if person and not role:
            raise ValidationError("Role is required when Person is filled.")

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


MovieCastFormSet = inlineformset_factory(
    Movie,
    MovieCast,
    form=MovieCastForm,
    extra=15,
    can_delete=True,
    labels={"person": "Entity"},
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)


class SeriesForm(forms.ModelForm):
    class Meta:
        model = Series
        exclude = ["created_by", "updated_by", "creators"]
        fields = "__all__"
        widgets = {
            "studios": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "distributors": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "based_on": autocomplete.ModelSelect2(
                url=reverse_lazy("read:work-autocomplete")
            ),
            "genres": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("watch:genre-autocomplete")
            ),
            "other_titles": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super(SeriesForm, self).__init__(*args, **kwargs)
        self.fields["studios_deprecated"].required = False
        self.fields["studios"].required = False
        self.fields["distributors"].required = False
        self.fields["genres"].required = False
        self.fields[
            "other_titles"
        ].help_text = (
            "e.g. translated titles in different languages, separated by slashes (`/`)."
        )


class SeriesRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta:
        model = SeriesRole
        fields = ("creator", "role", "domain", "alt_name")

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if person and not role:
            raise ValidationError("Role is required when Person is filled.")

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


SeriesRoleFormSet = inlineformset_factory(
    Series,
    SeriesRole,
    form=SeriesRoleForm,
    extra=15,
    can_delete=True,
    labels={"person": "Entity"},
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)


class EpisodeForm(forms.ModelForm):
    class Meta:
        model = Episode
        exclude = ["created_by", "updated_by", "creators", "casts"]
        fields = "__all__"

        widgets = {
            "other_titles": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super(EpisodeForm, self).__init__(*args, **kwargs)
        self.fields[
            "other_titles"
        ].help_text = (
            "e.g. translated titles in different languages, separated by slashes (`/`)."
        )
        self.fields["length"].help_text = "e.g. 45 mins, or 1:30:00"


class EpisodeRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta:
        model = EpisodeRole
        fields = ("creator", "role", "domain", "alt_name")

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if person and not role:
            raise ValidationError("Role is required when Person is filled.")

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


EpisodeRoleFormSet = inlineformset_factory(
    Episode,
    EpisodeRole,
    form=EpisodeRoleForm,
    extra=15,
    can_delete=True,
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)


class EpisodeCastForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta:
        model = EpisodeCast
        fields = ("creator", "role", "domain", "character_name")

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the person field is filled but the role field is not
        if person and not role:
            raise ValidationError("Role is required when Person is filled.")

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


EpisodeCastFormSet = inlineformset_factory(
    Episode,
    EpisodeCast,
    form=EpisodeCastForm,
    extra=15,
    can_delete=True,
    labels={"person": "Entity"},
    widgets={
        "person": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)


class WatchCheckInForm(forms.ModelForm):
    class Meta:
        model = WatchCheckIn
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
        super(WatchCheckInForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""
        self.fields["content"].required = False


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ["title", "notes"]


class ContentInCollectionForm(forms.ModelForm):
    content_url = forms.URLField()

    class Meta:
        model = ContentInCollection
        fields = ["content_url", "order"]
        exclude = ["collection"]

    def clean_content_url(self):
        content_url = self.cleaned_data.get("content_url")
        if not content_url:
            return content_url

        # Extracting movie or series ID from the URL
        content_id = re.findall(r"(movie|series)/(\d+)", content_url)
        if not content_id:
            raise forms.ValidationError("Invalid URL")

        content_type, object_id = content_id[0]
        try:
            if content_type == "movie":
                content_object = Movie.objects.get(pk=object_id)
            elif content_type == "series":
                content_object = Series.objects.get(pk=object_id)
        except (Movie.DoesNotExist, Series.DoesNotExist):
            raise forms.ValidationError("Content does not exist")

        self.instance.content_object = content_object
        return content_url

    def clean(self):
        cleaned_data = super().clean()
        content_url = cleaned_data.get("content_url")
        if not content_url:  # if the content_url field is empty
            self.cleaned_data["DELETE"] = True  # mark the form instance for deletion
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(ContentInCollectionForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.content_object:
            self.fields[
                "content_url"
            ].initial = f"{settings.ROOT_URL}/watch/{self.instance.content_type.model}/{self.instance.content_object.pk}"
        self.fields["content_url"].required = False
        self.fields["order"].required = False


ContentInCollectionFormSet = forms.inlineformset_factory(
    Collection,
    ContentInCollection,
    form=ContentInCollectionForm,
    extra=2,
    can_delete=True,
)
