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
    Episode,
    EpisodeCast,
    EpisodeRole,
    Movie,
    MovieCast,
    MovieInCollection,
    MovieRole,
    Series,
    SeriesInCollection,
    SeriesRole,
    WatchCheckIn,
)


class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        exclude = ["created_by", "updated_by", "persons", "casts"]
        fields = "__all__"
        widgets = {
            "studios": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("watch:studio-autocomplete")
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
        self.fields["studios"].required = False
        self.fields["genres"].required = False
        self.fields[
            "other_titles"
        ].help_text = (
            "e.g. translated titles in different languages, separated by slashes (`/`)."
        )


class MovieRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta:
        model = MovieRole
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


MovieRoleFormSet = inlineformset_factory(
    Movie,
    MovieRole,
    form=MovieRoleForm,
    extra=15,
    can_delete=True,
    labels={"person": "Entity"},
    widgets={
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


class MovieCastForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta:
        model = MovieCast
        fields = ("person", "role", "domain", "character_name")

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


MovieCastFormSet = inlineformset_factory(
    Movie,
    MovieCast,
    form=MovieCastForm,
    extra=15,
    can_delete=True,
    labels={"person": "Entity"},
    widgets={
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


class SeriesForm(forms.ModelForm):
    class Meta:
        model = Series
        exclude = ["created_by", "updated_by", "persons"]
        fields = "__all__"
        widgets = {
            "studios": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("watch:studio-autocomplete")
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
        self.fields["studios"].required = False
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


SeriesRoleFormSet = inlineformset_factory(
    Series,
    SeriesRole,
    form=SeriesRoleForm,
    extra=15,
    can_delete=True,
    labels={"person": "Entity"},
    widgets={
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


class EpisodeForm(forms.ModelForm):
    class Meta:
        model = Episode
        exclude = ["created_by", "updated_by", "persons", "casts"]
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


EpisodeRoleFormSet = inlineformset_factory(
    Episode,
    EpisodeRole,
    form=EpisodeRoleForm,
    extra=15,
    can_delete=True,
    widgets={
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


class EpisodeCastForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta:
        model = EpisodeCast
        fields = ("person", "role", "domain", "character_name")

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


EpisodeCastFormSet = inlineformset_factory(
    Episode,
    EpisodeCast,
    form=EpisodeCastForm,
    extra=15,
    can_delete=True,
    labels={"person": "Entity"},
    widgets={
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
        fields = ["title", "description"]


class MovieInCollectionForm(forms.ModelForm):
    movie_url = forms.URLField()

    class Meta:
        model = MovieInCollection
        fields = ["movie_url", "order"]
        exclude = ["collection"]

    def clean_movie_url(self):
        movie_url = self.cleaned_data.get("movie_url")
        if not movie_url:
            return movie_url
        movie_id = re.findall(r"movie/(\d+)", movie_url)
        if not movie_id:
            raise forms.ValidationError("Invalid Movie URL")
        try:
            movie = Movie.objects.get(pk=movie_id[0])
        except Movie.DoesNotExist:
            raise forms.ValidationError("Movie does not exist")
        self.instance.movie = movie
        return movie_url

    def __init__(self, *args, **kwargs):
        super(MovieInCollectionForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.movie:
            self.fields[
                "movie_url"
            ].initial = f"{settings.ROOT_URL}/watch/movie/{self.instance.movie.pk}"
        self.fields["movie_url"].required = False
        self.fields["order"].required = False


MovieInCollectionFormSet = forms.inlineformset_factory(
    Collection, MovieInCollection, form=MovieInCollectionForm, extra=2, can_delete=True
)


class SeriesInCollectionForm(forms.ModelForm):
    series_url = forms.URLField()

    class Meta:
        model = SeriesInCollection
        fields = ["series_url", "order"]
        exclude = ["collection"]

    def clean_series_url(self):
        series_url = self.cleaned_data.get("series_url")
        if not series_url:
            return series_url
        series_id = re.findall(r"series/(\d+)", series_url)
        if not series_id:
            raise forms.ValidationError("Invalid Series URL")
        try:
            series = Series.objects.get(pk=series_id[0])
        except Series.DoesNotExist:
            raise forms.ValidationError("Series does not exist")
        self.instance.series = series
        return series_url

    def __init__(self, *args, **kwargs):
        super(SeriesInCollectionForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.series:
            self.fields[
                "series_url"
            ].initial = f"{settings.ROOT_URL}/watch/series/{self.instance.series.pk}"
        self.fields["series_url"].required = False
        self.fields["order"].required = False


SeriesInCollectionFormSet = forms.inlineformset_factory(
    Collection,
    SeriesInCollection,
    form=SeriesInCollectionForm,
    extra=2,
    can_delete=True,
)
