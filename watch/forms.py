import re

import auto_prefetch
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
    class Meta(auto_prefetch.Model.Meta):
        model = Movie
        exclude = ["created_by", "updated_by", "creators", "casts", "locked"]
        fields = "__all__"
        widgets = {
            "studios": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "distributors": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "stars": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:creator-autocomplete")
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
            "genres": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("watch:genre-autocomplete")
            ),
            "other_titles": forms.TextInput(),
            "filming_locations": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("visit:location-autocomplete")
            ),
            "setting_locations": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("visit:location-autocomplete")
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
            "soundtracks": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:release-autocomplete")
            ),
            "tracks": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:track-autocomplete")
            ),
            "theme_songs": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:track-autocomplete")
            ),
            "ending_songs": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:track-autocomplete")
            ),
        }
        help_texts = {
            "other_titles": "e.g. translated titles in different languages, separated by slashes (`/`).",
            "filming_locations": "Locations of where the movie was filmed. <a href='/visit/location/create/'>Add a new location</a>.",
            "setting_locations": "Locations of where the movie was set. <a href='/visit/location/create/'>Add a new location</a>.",
            "studios": "Production companies. <a href='/entity/company/create/'>Add a new company</a>.",
            "distributors": "Distribution companies. <a href='/entity/company/create/'>Add a new company</a>.",
            "stars": "Main casts of the movie. <a href='/entity/creator/create/'>Add a new creator</a>.",
        }
        labels = {
            "imdb": "IMDB URL",
            "wikipedia": "Wikipedia URL",
            "official_website": "Official Website",
            "based_on_litworks": "Publications (Work)",
            "based_on_games": "Games (Work)",
            "based_on_movies": "Movies",
            "based_on_series": "Series",
            "mentioned_litworks": "Works",
            "mentioned_litinstances": "Instances",
            "mentioned_books": "Books",
            "mentioned_gameworks": "Works",
            "mentioned_games": "Games",
            "mentioned_movies": "Movies",
            "mentioned_series": "Series",
            "mentioned_musicalworks": "Works",
            "mentioned_tracks": "Tracks",
            "mentioned_releases": "Releases",
            "mentioned_locations": "Locations",
            "soundtracks": "Official Soundtracks (OST)",
            "tracks": "Tracks featured in the movie",
            "theme_songs": "Theme Songs",
            "ending_songs": "Ending Songs",
        }

    def __init__(self, *args, **kwargs):
        super(MovieForm, self).__init__(*args, **kwargs)
        self.fields["studios"].required = False
        self.fields["distributors"].required = False
        self.fields["genres"].required = False
        self.fields["filming_locations"].required = False
        self.fields["setting_locations"].required = False


class MovieReleaseDateForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = MovieReleaseDate
        fields = ("release_type", "region", "notes", "release_date")

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
    extra=1,
    can_delete=True,
)


class MovieRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = MovieRole
        fields = ("creator", "role", "domain", "alt_name")

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the creator field is filled but the role field is not
        if creator and not role:
            raise ValidationError("Role is required when Creator is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.creator is None:  # if the creator field is empty
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
    extra=1,
    can_delete=True,
    widgets={
        "creator": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
    help_texts={
        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
    },
)


class MovieCastForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = MovieCast
        fields = ("creator", "role", "domain", "character_name")

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the creator field is filled but the role field is not
        if creator and not role:
            raise ValidationError("Role is required when Creator is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.creator is None:  # if the creator field is empty
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
    extra=1,
    can_delete=True,
    widgets={
        "creator": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
    help_texts={
        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
    },
)


class SeriesForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Series
        exclude = ["created_by", "updated_by", "creators", "locked"]
        fields = "__all__"
        widgets = {
            "studios": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "distributors": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:company-autocomplete")
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
            "soundtracks": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:release-autocomplete")
            ),
            "genres": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("watch:genre-autocomplete")
            ),
            "other_titles": forms.TextInput(),
            "stars": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:creator-autocomplete")
            ),
        }
        help_texts = {
            "other_titles": "e.g. translated titles in different languages, separated by slashes (`/`).",
            "studios": "Production companies. <a href='/entity/company/create/'>Add a new company</a>.",
            "distributors": "Distribution companies. <a href='/entity/company/create/'>Add a new company</a>.",
            "based_on": "The original work that the movie is based on. <a href='/read/work/create/'>Add a new work</a>.",
            "stars": "Main casts of the series. <a href='/entity/creator/create/'>Add a new creator</a>. For episode-specific casts, add them in the Episode form.",
        }
        labels = {
            "based_on_litworks": "Publications (Work)",
            "based_on_games": "Games (Work)",
            "based_on_movies": "Movies",
            "based_on_series": "Series",
            "soundtracks": "Official Soundtracks (OST)",
        }

    def __init__(self, *args, **kwargs):
        super(SeriesForm, self).__init__(*args, **kwargs)
        self.fields["studios"].required = False
        self.fields["distributors"].required = False
        self.fields["genres"].required = False
        self.fields["other_titles"].help_text = (
            "e.g. translated titles in different languages, separated by slashes (`/`)."
        )


class SeriesRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = SeriesRole
        fields = ("creator", "role", "domain", "alt_name")

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the creator field is filled but the role field is not
        if creator and not role:
            raise ValidationError("Role is required when Creator is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.creator is None:  # if the creator field is empty
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
    extra=1,
    can_delete=True,
    widgets={
        "creator": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
    help_texts={
        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
    },
)


class EpisodeForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Episode
        exclude = ["created_by", "updated_by", "creators", "casts", "locked"]
        fields = "__all__"

        widgets = {
            "other_titles": forms.TextInput(),
            "filming_locations": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("visit:location-autocomplete")
            ),
            "setting_locations": autocomplete.ModelSelect2Multiple(
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
            "tracks": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:track-autocomplete")
            ),
            "theme_songs": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:track-autocomplete")
            ),
            "ending_songs": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("listen:track-autocomplete")
            ),
        }
        help_texts = {
            "filming_locations": "Locations of where the episode was filmed. <a href='/visit/location/create/'>Add a new location</a>.",
            "setting_locations": "Locations of where the episode was set. <a href='/visit/location/create/'>Add a new location</a>.",
            "release_date": "YYYY.MM.DD",
        }
        labels = {
            "based_on_litworks": "Publications (Work)",
            "based_on_games": "Games (Work)",
            "based_on_movies": "Movies",
            "based_on_series": "Series",
            "mentioned_litworks": "Works",
            "mentioned_litinstances": "Instances",
            "mentioned_books": "Books",
            "mentioned_gameworks": "Works",
            "mentioned_games": "Games",
            "mentioned_movies": "Movies",
            "mentioned_series": "Series",
            "mentioned_musicalworks": "Works",
            "mentioned_tracks": "Tracks",
            "mentioned_releases": "Releases",
            "mentioned_locations": "Locations",
            "tracks": "Tracks featured in the Episode",
            "theme_songs": "Theme Songs",
            "ending_songs": "Ending Songs",
        }

    def __init__(self, *args, **kwargs):
        super(EpisodeForm, self).__init__(*args, **kwargs)
        self.fields["other_titles"].help_text = (
            "e.g. translated titles in different languages, separated by slashes (`/`)."
        )
        self.fields["filming_locations"].required = False
        self.fields["setting_locations"].required = False
        self.fields["length"].help_text = "e.g. 45 mins, or 1:30:00"


class EpisodeRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = EpisodeRole
        fields = ("creator", "role", "domain", "alt_name")

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the creator field is filled but the role field is not
        if creator and not role:
            raise ValidationError("Role is required when Creator is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.creator is None:  # if the creator field is empty
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
    extra=1,
    can_delete=True,
    widgets={
        "creator": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
    help_texts={
        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
    },
)


class EpisodeCastForm(forms.ModelForm):
    domain = forms.CharField(initial="watch", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = EpisodeCast
        fields = ("creator", "role", "domain", "character_name")

    def clean(self):
        cleaned_data = super().clean()
        creator = cleaned_data.get("creator")
        role = cleaned_data.get("role")

        # if the creator field is filled but the role field is not
        if creator and not role:
            raise ValidationError("Role is required when Creator is filled.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.creator is None:  # if the creator field is empty
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
    extra=1,
    can_delete=True,
    widgets={
        "creator": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:creator-autocomplete"),
            attrs={"data-create-url": reverse_lazy("entity:creator_create")},
        ),
        "role": autocomplete.ModelSelect2(
            url=reverse_lazy("entity:role-autocomplete"),
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
    help_texts={
        "creator": "<a href='/entity/creator/create/'>Add a new creator</a>.",
        "role": "<a href='/entity/role/create/'>Add a new role</a>.",
    },
)


class WatchCheckInForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
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
    class Meta(auto_prefetch.Model.Meta):
        model = Collection
        fields = ["title", "notes"]


class ContentInCollectionForm(forms.ModelForm):
    content_url = forms.URLField()

    class Meta(auto_prefetch.Model.Meta):
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
            self.fields["content_url"].initial = (
                f"{settings.ROOT_URL}/watch/{self.instance.content_type.model}/{self.instance.content_object.pk}"
            )
        self.fields["content_url"].required = False
        self.fields["order"].required = False


ContentInCollectionFormSet = forms.inlineformset_factory(
    Collection,
    ContentInCollection,
    form=ContentInCollectionForm,
    extra=2,
    can_delete=True,
)
