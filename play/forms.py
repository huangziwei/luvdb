import re

from crispy_forms.bootstrap import Field
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Fieldset, Layout, Row, Submit
from dal import autocomplete
from django import forms
from django.conf import settings
from django.forms import inlineformset_factory
from django.urls import reverse_lazy

from .models import (
    Game,
    GameCast,
    GameCheckIn,
    GameInSeries,
    GameRole,
    GameSeries,
    Work,
    WorkRole,
)


class WorkForm(forms.ModelForm):
    class Meta:
        model = Work
        exclude = ["created_by", "updated_by", "persons", "casts"]
        fields = "__all__"
        widgets = {
            "developers": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("play:developer-autocomplete")
            ),
        }

    def __init__(self, *args, **kwargs):
        super(WorkForm, self).__init__(*args, **kwargs)
        self.fields["developers"].required = False


class WorkRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="play", widget=forms.HiddenInput())

    class Meta:
        model = WorkRole
        fields = ("person", "role", "domain", "alt_name")


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
            forward=["domain"],
            attrs={"data-create-url": reverse_lazy("entity:role_create")},
        ),
    },
)


class GameForm(forms.ModelForm):
    class Meta:
        model = Game
        exclude = ["created_by", "updated_by", "persons", "casts"]
        fields = "__all__"
        widgets = {
            "work": autocomplete.ModelSelect2(
                url=reverse_lazy("play:work-autocomplete")
            ),
            "developers": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("play:developer-autocomplete")
            ),
            "platforms": autocomplete.ModelSelect2Multiple(
                url=reverse_lazy("play:platform-autocomplete")
            ),
        }

    def __init__(self, *args, **kwargs):
        super(GameForm, self).__init__(*args, **kwargs)
        self.fields["developers"].required = False
        self.fields["platforms"].required = False


class GameRoleForm(forms.ModelForm):
    domain = forms.CharField(initial="play", widget=forms.HiddenInput())

    class Meta:
        model = GameRole
        fields = ("person", "role", "domain", "alt_name")


GameRoleFormSet = inlineformset_factory(
    Game,
    GameRole,
    form=GameRoleForm,
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


class GameCastForm(forms.ModelForm):
    domain = forms.CharField(initial="play", widget=forms.HiddenInput())

    class Meta:
        model = GameCast
        fields = ("person", "role", "domain", "character_name")


GameCastFormSet = inlineformset_factory(
    Game,
    GameCast,
    form=GameCastForm,
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


class GameCheckInForm(forms.ModelForm):
    class Meta:
        model = GameCheckIn
        fields = [
            "game",
            "user",
            "status",
            "progress",
            "progress_type",
            "content",
            "comments_enabled",
            "share_to_feed",
        ]
        widgets = {
            "game": forms.HiddenInput(),
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
        super(GameCheckInForm, self).__init__(*args, **kwargs)
        self.fields["content"].label = ""
        self.fields["content"].required = False
        self.fields["comments_enabled"].label = "Enable comments"


class GameSeriesForm(forms.ModelForm):
    class Meta:
        model = GameSeries
        fields = ["title"]


class GameInSeriesForm(forms.ModelForm):
    game_url = forms.URLField()

    class Meta:
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
