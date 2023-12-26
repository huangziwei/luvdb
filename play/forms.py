import re

import auto_prefetch
from dal import autocomplete
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from .models import (
    DLC,
    DLCCast,
    DLCRole,
    Game,
    GameCast,
    GameInSeries,
    GameReleaseDate,
    GameRole,
    GameSeries,
    PlayCheckIn,
    Work,
    WorkRole,
)


class WorkForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Work
        exclude = ["created_by", "updated_by", "creators", "casts", "locked"]
        fields = "__all__"
        widgets = {
            "developers": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "genres": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("play:genre-autocomplete")
            ),
            "other_titles": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super(WorkForm, self).__init__(*args, **kwargs)
        self.fields["developers"].required = False
        self.fields["genres"].required = False
        self.fields[
            "other_titles"
        ].help_text = (
            "e.g. translated titles in different languages, separated by slashes (`/`)"
        )


class WorkRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="play", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = WorkRole
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


WorkRoleFormSet = inlineformset_factory(
    Work,
    WorkRole,
    form=WorkRoleForm,
    extra=15,
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
)


class GameForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = Game
        exclude = ["created_by", "updated_by", "creators", "casts", "locked"]
        fields = "__all__"
        widgets = {
            "work": autocomplete.ModelSelect2(
                url=reverse_lazy("play:work-autocomplete")
            ),
            "developers": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "platforms": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("play:platform-autocomplete")
            ),
            "publishers": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("entity:company-autocomplete")
            ),
            "other_titles": forms.TextInput(),
            "rating": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super(GameForm, self).__init__(*args, **kwargs)
        self.fields["developers"].required = False
        self.fields["platforms"].required = False
        self.fields["publishers"].required = False
        self.fields[
            "other_titles"
        ].help_text = (
            "e.g. translated titles in different languages, separated by slashes (`/`)"
        )
        self.fields[
            "rating"
        ].help_text = (
            "e.g. ESRB, PEGI, CERO, OFLC, USK, GRAC, VET, DJCTQ, IARC, ACB, GSRR"
        )


class GameReleaseDateForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = GameReleaseDate
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


GameReleaseDateFormSet = inlineformset_factory(
    Game,
    GameReleaseDate,
    form=GameReleaseDateForm,
    extra=15,
    can_delete=True,
)


class GameRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="play", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = GameRole
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


GameRoleFormSet = inlineformset_factory(
    Game,
    GameRole,
    form=GameRoleForm,
    extra=15,
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
)


class GameCastForm(forms.ModelForm):
    domain = forms.CharField(initial="play", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = GameCast
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


GameCastFormSet = inlineformset_factory(
    Game,
    GameCast,
    form=GameCastForm,
    extra=15,
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
)


class PlayCheckInForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = PlayCheckIn
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
            "user": forms.HiddenInput(),  # author is now included
            "content": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Check in...",
                    "id": "text-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super(PlayCheckInForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""
        self.fields["content"].required = False
        self.fields["comments_enabled"].label = "Enable replies"


class GameSeriesForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = GameSeries
        fields = ["title", "other_titles", "description", "wikipedia"]
        widgets = {
            "other_titles": forms.TextInput(),
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "id": "text-input",
                }
            ),
        }


class GameInSeriesForm(forms.ModelForm):
    game_url = forms.URLField()

    class Meta(auto_prefetch.Model.Meta):
        model = GameInSeries
        fields = ["game_url", "order"]
        exclude = ["series"]

    def clean_game_url(self):
        game_url = self.cleaned_data.get("game_url")
        if not game_url:  # if the field is empty, just return it
            return game_url
        game_id = re.findall(r"game/(\d+)", game_url)
        if not game_id:
            raise forms.ValidationError("Invalid Game URL")
        try:
            game = Game.objects.get(pk=game_id[0])
        except Game.DoesNotExist:
            raise forms.ValidationError("Game does not exist")
        self.instance.game = game  # save the game instance directly
        return game_url

    def clean(self):
        cleaned_data = super().clean()
        game_url = cleaned_data.get("game_url")
        if not game_url:  # if the game_url field is empty
            self.cleaned_data["DELETE"] = True  # mark the form for deletion
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(GameInSeriesForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.game:
            self.fields[
                "game_url"
            ].initial = f"{settings.ROOT_URL}/play/game/{self.instance.game.pk}"
        self.fields["game_url"].required = False
        self.fields["game_url"].label = "URL"
        self.fields["order"].required = False


GameInSeriesFormSet = forms.inlineformset_factory(
    GameSeries, GameInSeries, form=GameInSeriesForm, extra=2, can_delete=True
)


class DLCForm(forms.ModelForm):
    class Meta(auto_prefetch.Model.Meta):
        model = DLC
        exclude = ["created_by", "updated_by", "creators", "casts", "locked"]
        fields = "__all__"

        widgets = {
            "other_titles": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super(DLCForm, self).__init__(*args, **kwargs)
        self.fields[
            "other_titles"
        ].help_text = (
            "e.g. translated titles in different languages, separated by slashes (`/`)."
        )


class DLCRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="play", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = DLCRole
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


DLCRoleFormSet = inlineformset_factory(
    DLC,
    DLCRole,
    form=DLCRoleForm,
    extra=15,
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
)


class DLCCastForm(forms.ModelForm):
    domain = forms.CharField(initial="play", widget=forms.HiddenInput())

    class Meta(auto_prefetch.Model.Meta):
        model = DLCCast
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


DLCCastFormSet = inlineformset_factory(
    DLC,
    DLCCast,
    form=DLCCastForm,
    extra=15,
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
)
